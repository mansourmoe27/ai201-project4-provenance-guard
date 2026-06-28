import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path("logs.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    try:
        with LOG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def write_log_entry(entry: dict) -> dict:
    logs = read_log()
    entry["timestamp"] = _utc_now()
    logs.append(entry)

    with LOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    return entry


def get_recent_entries(limit: int = 20) -> list[dict]:
    return read_log()[-limit:]