"""GoGo horoscope source extraction helpers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOGO_SCRAPER = ROOT / "scripts" / "autopost" / "gogo_scrape.js"


def _condense_sign_source(text: str, *, max_sentences: int = 4, max_chars: int = 420) -> str:
    value = " ".join((text or "").split()).strip()
    if not value:
        return ""

    parts = re.split(r"(?<=[\.\!\?])\s+", value)
    kept = []
    for part in parts:
        cleaned = part.strip()
        if not cleaned:
            continue
        kept.append(cleaned)
        if len(kept) >= max_sentences:
            break

    condensed = " ".join(kept).strip() or value
    if len(condensed) <= max_chars:
        return condensed

    clipped = condensed[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{clipped}..." if clipped else condensed[:max_chars].strip()


def _run_gogo_scraper(mode: str, date_label: str) -> dict | None:
    node = shutil.which("node")
    if not node:
        print("[WARN] GoGo source skipped: node_not_found")
        return None
    if not GOGO_SCRAPER.exists():
        print("[WARN] GoGo source skipped: scraper_script_missing")
        return None

    try:
        completed = subprocess.run(
            [node, str(GOGO_SCRAPER), mode, date_label],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except Exception as exc:
        print(f"[WARN] GoGo source skipped: {type(exc).__name__}")
        return None

    if completed.returncode != 0:
        reason = (completed.stderr or completed.stdout or "").strip()
        if reason:
            print(f"[WARN] GoGo source skipped ({mode}): {reason[:300]}")
        else:
            print(f"[WARN] GoGo source skipped ({mode}): unknown_error")
        return None

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        print(f"[WARN] GoGo source skipped ({mode}): invalid_json")
        return None


def build_gogo_source_context(category: str, now_local: str) -> str | None:
    date_only = now_local.split()[0].strip()
    if not date_only:
        return None

    if category == "horoscope":
        payload = _run_gogo_scraper("calendar", date_only)
        if not payload:
            return None

        context_lines = [
            "Source: GoGo Цаг тооны бичиг (use these facts as source material, but rewrite in fresh wording).",
            f"Source URL: {payload.get('source_url', 'https://gogo.mn/horoscope')}",
        ]
        if payload.get("gregorian_date") and payload.get("weekday"):
            context_lines.append(
                f"Source date: {payload['gregorian_date']} / {payload['weekday']} гараг"
            )
        if payload.get("bilgiin_day") and payload.get("lunar_day_text"):
            context_lines.append(
                f"Bilgiin line: Билгийн тооллын {payload['bilgiin_day']}. {payload['lunar_day_text']}"
            )
        if payload.get("haircut_omen"):
            context_lines.append(f"Haircut omen: {payload['haircut_omen']}")
        if payload.get("sun_times"):
            context_lines.append(f"Sunrise/sunset: {payload['sun_times']}")
        if payload.get("good_times"):
            context_lines.append(f"Good times: {payload['good_times']}")
        if payload.get("travel"):
            context_lines.append(f"Travel direction: {payload['travel']}")
        if payload.get("haircut_line"):
            context_lines.append(f"Haircut line: {payload['haircut_line']}")
        if payload.get("summary"):
            context_lines.append(f"Summary paragraph: {payload['summary']}")
        return "\n".join(context_lines).strip()

    if category == "zodiac_horoscope":
        payload = _run_gogo_scraper("western_today", date_only)
        if not payload:
            return None

        context_lines = [
            "Source: GoGo Өрнийн зурхай / Өнөөдөр (use these sign texts as source material, but rewrite in fresh wording).",
            f"Source URL: {payload.get('source_url', 'https://gogo.mn/horoscope/western/today')}",
            f"Source date: {payload.get('source_date', date_only.replace('-', '/'))}",
        ]
        for entry in payload.get("entries", []):
            sign = str(entry.get("sign", "")).strip()
            text = str(entry.get("text", "")).strip()
            if sign and text:
                context_lines.append(f"{sign}: {text}")
        return "\n".join(context_lines).strip()

    if category == "weekly_horoscope":
        payload = _run_gogo_scraper("western_week", date_only)
        if not payload:
            return None

        context_lines = [
            "Source: GoGo Өрнийн зурхай / Энэ долоо хоног (use these sign texts as source material, but rewrite in fresh wording).",
            f"Source URL: {payload.get('source_url', 'https://gogo.mn/horoscope/western/week')}",
        ]
        if payload.get("source_range"):
            context_lines.append(f"Source range: {payload['source_range']}")
        for entry in payload.get("entries", []):
            sign = str(entry.get("sign", "")).strip()
            text = _condense_sign_source(
                str(entry.get("text", "")).strip(),
                max_sentences=2,
                max_chars=220,
            )
            if sign and text:
                context_lines.append(f"{sign}: {text}")
        return "\n".join(context_lines).strip()

    return None
