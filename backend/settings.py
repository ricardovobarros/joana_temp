import os
from pathlib import Path


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Variável de ambiente em falta: {name}")
    return value


SUPABASE_URL = _required("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_KEY = _required("SUPABASE_SERVICE_KEY")

MQTT_HOST = _required("MQTT_HOST")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USER = _required("MQTT_USER")
MQTT_PASS = _required("MQTT_PASS")
MQTT_CLIENT_ID = os.environ.get("MQTT_CLIENT_ID", "joana-backend")
TOPIC_PREFIX = os.environ.get("TOPIC_PREFIX", "joana")

APP_PASSWORD = _required("APP_PASSWORD")

STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).parent / "static"))
