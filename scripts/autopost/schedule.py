"""Category scheduling and pin category selection."""

from __future__ import annotations

import os
import re
from typing import Dict, List

from .constants import (
    CATEGORY_ALIASES,
    DAILY_SCHEDULE_CATEGORY_BY_HOUR,
    POST_CATEGORIES,
    SCHEDULE_SKIP_CATEGORY,
)
from .env import env_flag, now_in_content_timezone


def normalize_category(value: str) -> str:
    raw = (value or "").strip().lower()
    return CATEGORY_ALIASES.get(raw, raw)


def parse_categories(value: str) -> List[str]:
    parsed = [normalize_category(item) for item in value.split(",") if item.strip()]
    valid = [item for item in parsed if item in POST_CATEGORIES]
    return valid or ["insight", "horoscope", "mantra", "fact"]


def parse_pin_categories(value: str) -> List[str]:
    parsed = [normalize_category(item) for item in value.split(",") if item.strip()]
    valid = [item for item in parsed if item in POST_CATEGORIES]
    return valid or ["horoscope"]


def select_scheduled_category() -> str | None:
    if not env_flag("USE_TIME_SLOT_SCHEDULE", "1"):
        return None

    force_hour_raw = os.getenv("FORCE_SLOT_HOUR", "").strip()
    if force_hour_raw:
        try:
            hour = int(force_hour_raw)
            if 0 <= hour <= 23:
                selected = DAILY_SCHEDULE_CATEGORY_BY_HOUR.get(hour)
                if selected == "goodnight" and not env_flag("ENABLE_MIDNIGHT_POST", "1"):
                    return SCHEDULE_SKIP_CATEGORY
                return selected
        except ValueError:
            pass

    now_local = now_in_content_timezone()
    selected = DAILY_SCHEDULE_CATEGORY_BY_HOUR.get(now_local.hour)
    if not selected:
        return None
    if selected == "goodnight" and not env_flag("ENABLE_MIDNIGHT_POST", "1"):
        return SCHEDULE_SKIP_CATEGORY
    return selected


def determine_post_category(meta: Dict[str, str]) -> str:
    explicit = normalize_category(os.getenv("POST_CATEGORY", ""))
    if explicit in POST_CATEGORIES:
        return explicit

    scheduled = select_scheduled_category()
    if scheduled:
        return scheduled

    categories = parse_categories(os.getenv("AUTO_CATEGORIES", "insight,horoscope,mantra,fact"))
    last = normalize_category(meta.get("last_category", ""))
    if last in categories:
        idx = categories.index(last)
        return categories[(idx + 1) % len(categories)]
    return categories[0]


def pin_meta_key_for_category(category: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", category.strip().lower()) or "unknown"
    return f"scheduled_pinned_post_id_{slug}"
