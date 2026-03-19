"""Facebook Graph API operations for posting and pin management."""

from __future__ import annotations

import json
import mimetypes
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
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


def post_photo_to_facebook(
    page_id: str,
    page_access_token: str,
    image_path: str | Path,
    message: str = "",
) -> Dict[str, Any]:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(path)

    boundary = f"----CodexBoundary{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    image_bytes = path.read_bytes()

    parts: list[bytes] = []
    fields = {
        "access_token": page_access_token,
        "published": "true",
    }
    if message.strip():
        fields["message"] = message.strip()

    for name, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
        )

    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        (
            f'Content-Disposition: form-data; name="source"; filename="{path.name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(image_bytes)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)
    req = urllib.request.Request(
        f"https://graph.facebook.com/{page_id}/photos",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urlopen_with_retry(req, 60, "Facebook photo post request") as response:
        response_body = response.read().decode("utf-8")

    return json.loads(response_body)


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
