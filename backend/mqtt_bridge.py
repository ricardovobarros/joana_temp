import json
import logging
import threading
from datetime import timedelta

import certifi
import paho.mqtt.client as mqtt

import db
import settings

log = logging.getLogger("mqtt_bridge")

TOPIC_TEMP = f"{settings.TOPIC_PREFIX}/temp"
TOPIC_STATE = f"{settings.TOPIC_PREFIX}/timer/state"
TOPIC_CMD = f"{settings.TOPIC_PREFIX}/timer/cmd"
TOPIC_STATUS = f"{settings.TOPIC_PREFIX}/status"

# Diferença máxima para considerar que duas horas de início são o mesmo timer
SAME_SESSION_TOLERANCE = timedelta(minutes=2)

_lock = threading.Lock()
device_online = None
_client = None


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


def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        log.error("Falha ao ligar ao MQTT: %s", reason_code)
        return
    log.info("Ligado ao MQTT %s", settings.MQTT_HOST)
    client.subscribe([(TOPIC_TEMP, 1), (TOPIC_STATE, 1), (TOPIC_STATUS, 1)])


def _on_message(client, userdata, msg):
    global device_online
    try:
        text = msg.payload.decode()
        if msg.topic == TOPIC_STATUS:
            device_online = text == "online"
            return
        payload = json.loads(text)
        with _lock:
            if msg.topic == TOPIC_TEMP:
                if not msg.retain:
                    _handle_temp(payload)
            elif msg.topic == TOPIC_STATE:
                _handle_state(payload, msg.retain)
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


def stop():
    if _client is not None:
        _client.loop_stop()
        _client.disconnect()


def send_command(action: str) -> bool:
    if _client is None or not _client.is_connected():
        return False
    info = _client.publish(TOPIC_CMD, action, qos=1, retain=False)
    return info.rc == mqtt.MQTT_ERR_SUCCESS
