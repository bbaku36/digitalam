"""GoGo horoscope source extraction helpers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta
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


def _week_start(date_only: str) -> datetime:
    parsed = datetime.strptime(date_only, "%Y-%m-%d")
    return parsed - timedelta(days=parsed.weekday())


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
        monday = _week_start(date_only)
        sunday = monday + timedelta(days=6)
        entries: list[dict] = []
        for offset in range(7):
            current = monday + timedelta(days=offset)
            payload = _run_gogo_scraper("calendar_day", current.strftime("%Y-%m-%d"))
            if payload:
                entries.append(payload)

        if len(entries) < 7:
            return None

        context_lines = [
            "Source: GoGo Цаг тооны бичиг / 7 хоногийн өдөр тутмын эх сурвалж (use these facts as source material, but rewrite in fresh wording).",
            f"Source URL: {entries[0].get('source_url', 'https://gogo.mn/horoscope')}",
            f"Source endpoint: {entries[0].get('source_endpoint', 'https://gogo.mn/horoscope/daycolor')}",
            (
                "Week range: "
                f"{monday.year}.{monday.month:02d}.{monday.day:02d}-"
                f"{sunday.year}.{sunday.month:02d}.{sunday.day:02d}"
            ),
        ]
        for entry in entries:
            weekday = str(entry.get("weekday", "")).strip()
            gregorian_date = str(entry.get("gregorian_date", "")).strip()
            date_label = gregorian_date.replace(".", "-") if gregorian_date else ""
            if weekday:
                header = f"[{weekday} {date_label or entry.get('source_date', '')}]"
                context_lines.append(header)
            if entry.get("bilgiin_day") and entry.get("lunar_day_text"):
                context_lines.append(
                    f"Bilgiin line: Билгийн тооллын {entry['bilgiin_day']}. {entry['lunar_day_text']}"
                )
            if entry.get("haircut_omen"):
                context_lines.append(f"Haircut omen: {entry['haircut_omen']}")
            if entry.get("haircut_line"):
                context_lines.append(f"Haircut suitability: {entry['haircut_line']}")
            if entry.get("travel"):
                context_lines.append(f"Travel guidance: {entry['travel']}")
            if entry.get("good_activities"):
                context_lines.append(f"Good activities: {entry['good_activities']}")
            if entry.get("caution"):
                context_lines.append(f"Caution: {entry['caution']}")
            if entry.get("summary"):
                context_lines.append(
                    "Summary paragraph: "
                    + _condense_sign_source(
                        str(entry["summary"]).strip(),
                        max_sentences=4,
                        max_chars=360,
                    )
                )
        return "\n".join(context_lines).strip()

    return None
