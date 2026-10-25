from datetime import datetime, timedelta, timezone

import httpx

import settings

_HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_KEY,
    "Content-Type": "application/json",
}
# Chaves antigas (service_role) são JWT e vão também no Authorization;
# as novas (sb_secret_...) só podem ir no header apikey.
if settings.SUPABASE_SERVICE_KEY.startswith("eyJ"):
    _HEADERS["Authorization"] = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
_REST = f"{settings.SUPABASE_URL}/rest/v1"


def _request(method: str, table: str, *, params=None, json=None, prefer=None):
    headers = dict(_HEADERS)
    if prefer:
        headers["Prefer"] = prefer
    with httpx.Client(timeout=10) as client:
        response = client.request(method, f"{_REST}/{table}", params=params, json=json, headers=headers)
    response.raise_for_status()
    return response.json() if response.content else None


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def insert_reading(at: datetime, temperature_c: float, humidity):
    _request("POST", "temperature_readings", prefer="return=minimal", json={
        "created_at": at.isoformat(),
        "temperature_c": temperature_c,
        "humidity": humidity,
    })


def readings_since(since: datetime):
    return _request("GET", "temperature_readings", params={
        "select": "created_at,temperature_c,humidity",
        "created_at": f"gte.{since.isoformat()}",
        "order": "created_at.asc",
        "limit": "5000",
    })


def open_session():
    rows = _request("GET", "timer_sessions", params={
        "select": "*",
        "ended_at": "is.null",
        "limit": "1",
    })
    return rows[0] if rows else None


def latest_session():
    rows = _request("GET", "timer_sessions", params={
        "select": "*",
        "order": "started_at.desc",
        "limit": "1",
    })
    return rows[0] if rows else None


def start_session(started_at: datetime):
    _request("POST", "timer_sessions", prefer="return=minimal", json={
        "started_at": started_at.isoformat(),
    })


def close_session(session: dict, ended_at: datetime, reason: str, duration_seconds=None):
    if duration_seconds is None:
        started_at = parse_ts(session["started_at"])
        duration_seconds = max(0, int((ended_at - started_at).total_seconds()))
    duration_seconds = min(duration_seconds, 12 * 3600)
    _request("PATCH", "timer_sessions", params={"id": f"eq.{session['id']}"},
             prefer="return=minimal", json={
                 "ended_at": ended_at.isoformat(),
                 "duration_seconds": duration_seconds,
                 "end_reason": reason,
             })


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(days: int) -> datetime:
    return now_utc() - timedelta(days=days)
