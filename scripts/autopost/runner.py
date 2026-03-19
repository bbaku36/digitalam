"""Main execution flow for scheduled Facebook autoposting."""

from __future__ import annotations

import json
import os
import re
import urllib.error
from datetime import datetime, timezone
from typing import Dict

from .ai import get_last_ai_status
from .constants import SCHEDULE_SKIP_CATEGORY
from .content import build_category_post_bundle
from .env import env_flag, load_env_file
from .facebook import (
    post_photo_to_facebook,
    post_to_facebook,
    rotate_category_pin,
    rotate_weekly_pin,
    set_post_pin_state,
    should_pin_post,
)
from .image_cards import (
    build_horoscope_image_caption,
    cleanup_generated_card_assets,
    generate_horoscope_card_image,
)
from .notifications import notify_gemini_failure
from .schedule import determine_post_category, parse_pin_categories, pin_meta_key_for_category
from .state import load_post_meta, load_state, prune_state, save_post_meta, save_state


def main() -> int:
    load_env_file()

    dry_run = env_flag("DRY_RUN", "0")

    page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()
    page_access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    pin_access_token = (
        os.getenv("PIN_ACCESS_TOKEN", "").strip()
        or os.getenv("FACEBOOK_USER_ACCESS_TOKEN", "").strip()
        or page_access_token
    )
    scheduled_pin_categories = parse_pin_categories(
        os.getenv("PIN_CATEGORIES", "horoscope,zodiac_horoscope")
    )

    posted = prune_state(load_state())
    post_meta = load_post_meta()
    category = determine_post_category(post_meta)

    if category == SCHEDULE_SKIP_CATEGORY:
        print("[INFO] No scheduled category for this run, or the selected slot is disabled. Skipping this run.")
        return 0

    print(f"[INFO] Selected category: {category}")
    message, source_context = build_category_post_bundle(category)
    ai_status = get_last_ai_status()
    if bool(ai_status.get("gemini_failed", False)):
        notify_gemini_failure(category=category, ai_status=ai_status, dry_run=dry_run)
    require_ai_content = env_flag("REQUIRE_AI_CONTENT", "1")
    allow_source_first_horoscope = category == "horoscope" and bool(source_context)
    if require_ai_content and not bool(ai_status.get("used_ai", False)) and not allow_source_first_horoscope:
        reason = (
            str(ai_status.get("deepseek_failure_reason", "")).strip()
            or str(ai_status.get("gemini_failure_reason", "")).strip()
            or "ai_generation_failed"
        )
        print(f"[ERROR] REQUIRE_AI_CONTENT=1 but AI generation failed: {reason}")
        print("[ERROR] Skipping post to avoid non-AI fallback content.")
        return 1

    image_mode = category == "horoscope" and env_flag("HOROSCOPE_IMAGE_POST", "1")
    image_path = None
    image_caption = ""
    if image_mode:
        first_line = next((line.strip() for line in message.splitlines() if line.strip()), category)
        slug_tail = re.sub(r"[^0-9]+", "-", first_line).strip("-") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = f"{category}-{slug_tail}"
        try:
            image_path = generate_horoscope_card_image(
                post_text=message,
                source_context=source_context,
                slug=slug,
            )
            image_caption = build_horoscope_image_caption(message)
        except Exception as exc:
            print(f"[ERROR] Failed to generate horoscope image card: {exc}")
            return 1

    weekly_pinned_post_id = post_meta.get("weekly_pinned_post_id", "").strip()
    scheduled_pin_state_updates: Dict[str, str] = {}

    if dry_run:
        print("[DRY RUN] Generated message:\n")
        print(message)
        if image_path:
            print(f"\n[DRY RUN] Generated image: {image_path}")
            if image_caption:
                print("\n[DRY RUN] Image caption:\n")
                print(image_caption)
    else:
        if not page_id or not page_access_token:
            print("[ERROR] Missing FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN")
            return 1

        try:
            if image_path:
                result = post_photo_to_facebook(page_id, page_access_token, image_path, image_caption)
            else:
                result = post_to_facebook(page_id, page_access_token, message)
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            print("[ERROR] Facebook API error")
            print(details)
            return 1
        except Exception as exc:
            print(f"[ERROR] Failed to post to Facebook: {exc}")
            return 1

        post_id = result.get("post_id") or result.get("id", "unknown")
        print(f"[OK] Posted to Facebook. post_id={post_id}")

        if should_pin_post(category, scheduled_pin_categories) and post_id != "unknown":
            if category == "weekly":
                weekly_pinned_post_id = rotate_weekly_pin(pin_access_token, post_meta, post_id)
            elif env_flag("PIN_SCHEDULED_POSTS", "1") and category in scheduled_pin_categories:
                key = pin_meta_key_for_category(category)
                scheduled_pin_state_updates[key] = rotate_category_pin(
                    pin_access_token=pin_access_token,
                    post_meta=post_meta,
                    new_post_id=post_id,
                    category=category,
                )
            else:
                try:
                    pin_result = set_post_pin_state(pin_access_token, post_id, is_pinned=True)
                    print(f"[OK] Pinned post. result={json.dumps(pin_result, ensure_ascii=False)}")
                except urllib.error.HTTPError as exc:
                    details = exc.read().decode("utf-8", errors="replace")
                    print("[WARN] Failed to pin post via Facebook API")
                    print("[HINT] Provide PIN_ACCESS_TOKEN (user token with pages_manage_engagement).")
                    print(details)
                except Exception as exc:
                    print(f"[WARN] Failed to pin post: {exc}")

        if image_path:
            try:
                cleanup_generated_card_assets(image_path)
            except Exception as exc:
                print(f"[WARN] Failed to cleanup generated image assets: {exc}")

    now_iso = datetime.now(timezone.utc).isoformat()
    save_state(prune_state(posted))

    meta_to_save = dict(post_meta)
    meta_to_save["last_category"] = category
    meta_to_save["last_post_at"] = now_iso
    if weekly_pinned_post_id:
        meta_to_save["weekly_pinned_post_id"] = weekly_pinned_post_id

    for key, value in scheduled_pin_state_updates.items():
        if value:
            meta_to_save[key] = value

    save_post_meta(meta_to_save)
    return 0
