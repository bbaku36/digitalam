"""Facebook Graph API operations for posting and pin management."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from .env import env_flag
from .http import urlopen_with_retry
from .schedule import pin_meta_key_for_category


def post_to_facebook(page_id: str, page_access_token: str, message: str) -> Dict[str, Any]:
    url = f"https://graph.facebook.com/{page_id}/feed"
    payload = urllib.parse.urlencode(
        {
            "message": message,
            "access_token": page_access_token,
        }
    ).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    with urlopen_with_retry(req, 30, "Facebook post request") as response:
        body = response.read().decode("utf-8")

    return json.loads(body)


def set_post_pin_state(access_token: str, post_id: str, is_pinned: bool) -> Dict[str, Any]:
    url = f"https://graph.facebook.com/{post_id}"
    payload = urllib.parse.urlencode(
        {
            "is_pinned": "true" if is_pinned else "false",
            "access_token": access_token,
        }
    ).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    action = "pin" if is_pinned else "unpin"
    with urlopen_with_retry(req, 30, f"Facebook {action} request") as response:
        body = response.read().decode("utf-8")

    return json.loads(body)


def should_pin_post(category: str, pin_categories: List[str]) -> bool:
    if env_flag("PIN_POST", "0"):
        return True
    if category == "weekly" and env_flag("PIN_WEEKLY_POST", "1"):
        return True
    if env_flag("PIN_SCHEDULED_POSTS", "1") and category in pin_categories:
        return True
    return False


def rotate_weekly_pin(
    pin_access_token: str,
    post_meta: Dict[str, str],
    new_post_id: str,
) -> str:
    previous_pinned = post_meta.get("weekly_pinned_post_id", "").strip()

    if previous_pinned and previous_pinned != new_post_id:
        try:
            unpin_result = set_post_pin_state(pin_access_token, previous_pinned, is_pinned=False)
            print(f"[OK] Unpinned previous weekly post. result={json.dumps(unpin_result, ensure_ascii=False)}")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            print("[WARN] Failed to unpin previous weekly post via Facebook API")
            print(details)
        except Exception as exc:
            print(f"[WARN] Failed to unpin previous weekly post: {exc}")

    try:
        pin_result = set_post_pin_state(pin_access_token, new_post_id, is_pinned=True)
        print(f"[OK] Pinned weekly post. result={json.dumps(pin_result, ensure_ascii=False)}")
        return new_post_id
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print("[WARN] Failed to pin weekly post via Facebook API")
        print(details)
    except Exception as exc:
        print(f"[WARN] Failed to pin weekly post: {exc}")

    return previous_pinned or ""


def rotate_category_pin(
    pin_access_token: str,
    post_meta: Dict[str, str],
    new_post_id: str,
    category: str,
) -> str:
    key = pin_meta_key_for_category(category)
    previous_pinned = post_meta.get(key, "").strip()

    if previous_pinned and previous_pinned != new_post_id:
        try:
            unpin_result = set_post_pin_state(pin_access_token, previous_pinned, is_pinned=False)
            print(
                f"[OK] Unpinned previous {category} post. "
                f"result={json.dumps(unpin_result, ensure_ascii=False)}"
            )
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            print(f"[WARN] Failed to unpin previous {category} post via Facebook API")
            print(details)
        except Exception as exc:
            print(f"[WARN] Failed to unpin previous {category} post: {exc}")

    try:
        pin_result = set_post_pin_state(pin_access_token, new_post_id, is_pinned=True)
        print(f"[OK] Pinned {category} post. result={json.dumps(pin_result, ensure_ascii=False)}")
        return new_post_id
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"[WARN] Failed to pin {category} post via Facebook API")
        print(details)
    except Exception as exc:
        print(f"[WARN] Failed to pin {category} post: {exc}")

    return previous_pinned or ""
