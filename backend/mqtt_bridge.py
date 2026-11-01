import itertools
import json
import logging
import threading
from datetime import timedelta

import certifi
import paho.mqtt.client as mqtt

import db
import fan_speeds
import settings

log = logging.getLogger("mqtt_bridge")

TOPIC_TEMP = f"{settings.TOPIC_PREFIX}/temp"
TOPIC_STATE = f"{settings.TOPIC_PREFIX}/timer/state"
TOPIC_CMD = f"{settings.TOPIC_PREFIX}/timer/cmd"
TOPIC_STATUS = f"{settings.TOPIC_PREFIX}/status"
TOPIC_POWER_OVERRIDE = f"{settings.TOPIC_PREFIX}/plug/override"
TOPIC_SLEEP_STATE = f"{settings.TOPIC_PREFIX}/sleep/state"

# Shelly Plug M Gen3 (API Gen2+). As respostas RPC chegam em "<src>/rpc".
TOPIC_PLUG_ONLINE = f"{settings.PLUG_TOPIC_PREFIX}/online"
TOPIC_PLUG_STATUS = f"{settings.PLUG_TOPIC_PREFIX}/status/switch:0"
TOPIC_PLUG_EVENTS = f"{settings.PLUG_TOPIC_PREFIX}/events/rpc"
TOPIC_PLUG_RPC = f"{settings.PLUG_TOPIC_PREFIX}/rpc"
TOPIC_PLUG_REPLIES = f"{settings.MQTT_CLIENT_ID}/rpc"

# Diferença máxima para considerar que duas horas de início são o mesmo timer
SAME_SESSION_TOLERANCE = timedelta(minutes=2)

PLUG_POLL_S = 30
# Sem notícias da tomada há mais do que isto, conta como offline
PLUG_STALE = timedelta(seconds=PLUG_POLL_S * 3)

_lock = threading.Lock()
device_online = None
_client = None

_plug_lock = threading.Lock()
_plug = {"online": None, "output": None, "watts": None, "updated_at": None}
_rpc_ids = itertools.count(1)
_stop = threading.Event()


def _handle_temp(payload: dict):
    at = db.now_utc() - timedelta(seconds=int(payload.get("ago_s", 0)))
    db.insert_reading(at, float(payload["t"]), payload.get("h"))
    log.info("Temperatura %s C gravada (%s)", payload["t"], at.isoformat())


def _ensure_open(started_at):
    session = db.open_session()
    if session is None:
        db.start_session(started_at)
        return
    if abs(db.parse_ts(session["started_at"]) - started_at) > SAME_SESSION_TOLERANCE:
        db.close_session(session, started_at, "unknown")
        db.start_session(started_at)


def _ensure_closed(ended_at, reason, duration_seconds=None):
    session = db.open_session()
    if session is not None:
        db.close_session(session, ended_at, reason, duration_seconds)


def _handle_state(payload: dict, retained: bool):
    event = payload.get("event")
    running = bool(payload.get("running"))
    elapsed = int(payload.get("elapsed_s", 0))
    event_at = db.now_utc() - timedelta(seconds=int(payload.get("ago_s", 0)))

    # Mensagens retidas e "sync" só reconciliam o estado: as horas
    # que trazem podem estar desatualizadas.
    if retained or event == "sync":
        if running:
            if db.open_session() is None:
                db.start_session(event_at - timedelta(seconds=elapsed))
        else:
            _ensure_closed(db.now_utc(), "reboot")
        return

    if event == "start":
        _ensure_open(event_at - timedelta(seconds=elapsed))
    elif event == "stop":
        _ensure_closed(event_at, payload.get("reason", "unknown"), elapsed)
    log.info("Timer %s (%s)", event, payload.get("reason"))


def _handle_sleep(payload: dict, retained: bool):
    event = payload.get("event")
    sleeping = bool(payload.get("sleeping"))
    event_at = db.now_utc() - timedelta(seconds=int(payload.get("ago_s", 0)))
    session = db.open_sleep_session()

    # Mensagem retida/sync reconcilia o estado após uma reinicialização sem
    # duplicar um toque que o backend já tenha gravado.
    if retained or event == "sync":
        if sleeping and session is None:
            db.start_sleep_session(event_at)
        elif not sleeping and session is not None:
            db.close_sleep_session(session, event_at, "reboot")
        return

    if event == "sleep" and session is None:
        db.start_sleep_session(event_at)
    elif event == "wake" and session is not None:
        db.close_sleep_session(session, event_at, payload.get("reason", "button"))
    log.info("Bebé: %s", "dormiu" if sleeping else "acordou")


def _update_plug(status: dict):
    with _plug_lock:
        if "output" in status:
            _plug["output"] = bool(status["output"])
        if "apower" in status:
            _plug["watts"] = float(status["apower"])
        _plug["updated_at"] = db.now_utc()


def _handle_plug(topic: str, text: str):
    if topic == TOPIC_PLUG_ONLINE:
        with _plug_lock:
            _plug["online"] = text.strip() == "true"
        return
    message = json.loads(text)
    if topic == TOPIC_PLUG_STATUS:
        _update_plug(message)
    elif topic == TOPIC_PLUG_EVENTS:
        if message.get("method") in ("NotifyStatus", "NotifyFullStatus"):
            switch = message.get("params", {}).get("switch:0")
            if switch:
                _update_plug(switch)
    elif topic == TOPIC_PLUG_REPLIES:
        if "error" in message:
            log.warning("Erro RPC da tomada: %s", message["error"])
            return
        result = message.get("result")
        if isinstance(result, dict) and ("output" in result or "apower" in result):
            _update_plug(result)


def _plug_rpc(method: str, params: dict) -> bool:
    if _client is None or not _client.is_connected():
        return False
    request = {"id": next(_rpc_ids), "src": settings.MQTT_CLIENT_ID,
               "method": method, "params": params}
    info = _client.publish(TOPIC_PLUG_RPC, json.dumps(request), qos=1)
    return info.rc == mqtt.MQTT_ERR_SUCCESS


def _poll_plug():
    while not _stop.wait(PLUG_POLL_S):
        _plug_rpc("Switch.GetStatus", {"id": 0})


def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        log.error("Falha ao ligar ao MQTT: %s", reason_code)
        return
    log.info("Ligado ao MQTT %s", settings.MQTT_HOST)
    client.subscribe([
        (TOPIC_TEMP, 1), (TOPIC_STATE, 1), (TOPIC_STATUS, 1),
        (TOPIC_POWER_OVERRIDE, 1), (TOPIC_SLEEP_STATE, 1),
        (TOPIC_PLUG_ONLINE, 1), (TOPIC_PLUG_STATUS, 1),
        (TOPIC_PLUG_EVENTS, 1), (TOPIC_PLUG_REPLIES, 1),
    ])
    _plug_rpc("Switch.GetStatus", {"id": 0})


def _on_message(client, userdata, msg):
    global device_online
    try:
        text = msg.payload.decode()
        if msg.topic == TOPIC_STATUS:
            device_online = text == "online"
            return
        if msg.topic == TOPIC_POWER_OVERRIDE:
            # O botão físico apenas restaura energia; nunca a corta.
            if set_plug(True):
                log.info("Override físico: energia da tomada ligada")
            return
        if msg.topic in (TOPIC_PLUG_ONLINE, TOPIC_PLUG_STATUS,
                         TOPIC_PLUG_EVENTS, TOPIC_PLUG_REPLIES):
            _handle_plug(msg.topic, text)
            return
        payload = json.loads(text)
        with _lock:
            if msg.topic == TOPIC_TEMP:
                if not msg.retain:
                    _handle_temp(payload)
            elif msg.topic == TOPIC_STATE:
                _handle_state(payload, msg.retain)
            elif msg.topic == TOPIC_SLEEP_STATE:
                _handle_sleep(payload, msg.retain)
    except Exception:
        log.exception("Erro a processar %s: %r", msg.topic, msg.payload)


def start():
    global _client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.MQTT_CLIENT_ID)
    client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASS)
    client.tls_set(ca_certs=certifi.where())
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect_async(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=60)
    client.loop_start()
    _client = client
    threading.Thread(target=_poll_plug, name="plug-poll", daemon=True).start()


def stop():
    _stop.set()
    if _client is not None:
        _client.loop_stop()
        _client.disconnect()


def send_command(action: str) -> bool:
    if _client is None or not _client.is_connected():
        return False
    info = _client.publish(TOPIC_CMD, action, qos=1, retain=False)
    return info.rc == mqtt.MQTT_ERR_SUCCESS


def fan_status() -> dict:
    with _plug_lock:
        plug = dict(_plug)
    updated_at = plug["updated_at"]
    fresh = updated_at is not None and db.now_utc() - updated_at < PLUG_STALE
    online = plug["online"] is not False and fresh
    if not online:
        state, speed = "unknown", None
    elif plug["output"] is False:
        state, speed = "off", None
    else:
        state, speed = fan_speeds.classify(plug["watts"])
    return {
        "plug_online": online,
        "plug_on": plug["output"],
        "watts": plug["watts"],
        "state": state,
        "speed": speed,
    }


def set_plug(on: bool) -> bool:
    if not _plug_rpc("Switch.Set", {"id": 0, "on": on}):
        return False
    _plug_rpc("Switch.GetStatus", {"id": 0})
    return True
