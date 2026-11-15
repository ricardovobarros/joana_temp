import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import mqtt_bridge
import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_bridge.start()
    yield
    mqtt_bridge.stop()


app = FastAPI(title="joana_temp", lifespan=lifespan)

# O DHT11 lê cerca de 2 °C acima da temperatura do quarto.
TEMPERATURE_OFFSET_C = -2.0


class TimerBody(BaseModel):
    action: Literal["start", "stop"]


class FanBody(BaseModel):
    action: Literal["off", "plug_on"]


class SleepBody(BaseModel):
    action: Literal["sleep", "wake"]


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard():
    readings = db.readings_since(db.days_ago(7))
    session = db.latest_session()
    running = session is not None and session["ended_at"] is None
    return {
        "device_online": mqtt_bridge.device_online,
        "server_time": db.now_utc().isoformat(),
        "readings": [
            {"at": r["created_at"],
             "t": round(float(r["temperature_c"]) + TEMPERATURE_OFFSET_C, 1),
             "h": float(r["humidity"]) if r["humidity"] is not None else None}
            for r in readings
        ],
        "timer": {"running": running},
        "last_session": session,
        "fan": mqtt_bridge.fan_status(),
    }


@app.get("/api/sleep")
def sleep_dashboard():
    events = db.sleep_events_since(db.days_ago(30))
    return {
        "device_online": mqtt_bridge.device_online,
        "server_time": db.now_utc().isoformat(),
        "events": [
            {"at": event["happened_at"], "kind": event["kind"]}
            for event in events
        ],
    }


@app.post("/api/sleep")
def set_sleep(body: SleepBody):
    now = db.now_utc()
    # Cada toque grava o seu horário. Dormir e acordar não precisam de par.
    db.insert_sleep_event(now, body.action, "app")

    # O ESP32 é um controlo opcional. Quando estiver ligado, mostra o rostinho;
    # uma falha de MQTT nunca impede o registo no Supabase.
    mqtt_bridge.send_sleep_command(body.action)
    return {"ok": True, "action": body.action}


@app.post("/api/timer")
def timer(body: TimerBody):
    now = db.now_utc()
    session = db.open_session()
    if body.action == "start":
        if session is None:
            db.start_session(now)
    elif session is not None:
        db.close_session(session, now, "app")

    # Publica apenas para manter o hardware alinhado quando ele estiver online.
    # A fonte de verdade do app é a sessão persistida acima.
    mqtt_bridge.send_command(body.action)
    return {"ok": True, "action": body.action}


@app.post("/api/fan")
def fan(body: FanBody):
    if not mqtt_bridge.fan_status()["plug_online"]:
        raise HTTPException(status_code=503, detail="Tomada do ventilador offline")
    if not mqtt_bridge.set_plug(body.action == "plug_on"):
        raise HTTPException(status_code=503, detail="Servidor MQTT indisponível")
    return {"ok": True, "action": body.action}


if settings.STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=settings.STATIC_DIR, html=True), name="site")
