"""State persistence for posted items and metadata."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / ".state"
STATE_FILE = STATE_DIR / "posted_items.json"
POST_META_FILE = STATE_DIR / "post_meta.json"


def load_state() -> Dict[str, str]:
    if not STATE_FILE.exists():
        return {}

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass

    return {}


def save_state(data: Dict[str, str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_post_meta() -> Dict[str, str]:
    if not POST_META_FILE.exists():
        return {}
    try:
        data = json.loads(POST_META_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_post_meta(meta: Dict[str, str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    POST_META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def prune_state(posted: Dict[str, str], keep_days: int = 14) -> Dict[str, str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    cleaned: Dict[str, str] = {}

    for key, timestamp in posted.items():
        try:
            dt = datetime.fromisoformat(timestamp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                cleaned[key] = dt.astimezone(timezone.utc).isoformat()
        except Exception:
            continue

    return cleaned
