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


class TimerBody(BaseModel):
    action: Literal["start", "stop"]


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
            {"at": r["created_at"], "t": float(r["temperature_c"]),
             "h": float(r["humidity"]) if r["humidity"] is not None else None}
            for r in readings
        ],
        "timer": {"running": running},
        "last_session": session,
    }


@app.post("/api/timer")
def timer(body: TimerBody):
    if mqtt_bridge.device_online is False:
        raise HTTPException(status_code=503, detail="ESP32 offline")
    if not mqtt_bridge.send_command(body.action):
        raise HTTPException(status_code=503, detail="Servidor MQTT indisponível")
    return {"ok": True, "action": body.action}


if settings.STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=settings.STATIC_DIR, html=True), name="site")
