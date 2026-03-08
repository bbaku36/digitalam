"""Failure notifications for AI/provider issues."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Mapping

from .env import env_flag
from .http import urlopen_with_retry


def _post_json(url: str, payload: dict, label: str) -> bool:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen_with_retry(req, 20, label):
            return True
    except Exception as exc:
        print(f"[WARN] {label} failed: {exc}")
        return False


def _send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urlopen_with_retry(req, 20, "Telegram alert request"):
            return True
    except Exception as exc:
        print(f"[WARN] Telegram alert failed: {exc}")
        return False


def notify_gemini_failure(
    *,
    category: str,
    ai_status: Mapping[str, str | bool],
    dry_run: bool,
) -> None:
    if not env_flag("ALERT_ON_GEMINI_FAILURE", "1"):
        return
    if dry_run and not env_flag("ALERT_ON_DRY_RUN", "0"):
        return

    reason = str(ai_status.get("gemini_failure_reason", "unknown"))
    provider_used = str(ai_status.get("provider_used", "")) or "fallback"

    message = (
        "Digitalam alert: Gemini generation failed.\n"
        f"Category: {category}\n"
        f"Reason: {reason}\n"
        f"Fallback provider used: {provider_used}\n"
        "Action: check API key/quota/model/network."
    )

    sent = False

    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if webhook_url:
        sent = _post_json(
            webhook_url,
            {"text": message, "category": category, "reason": reason},
            "Webhook alert request",
        ) or sent

    tg_bot = os.getenv("ALERT_TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.getenv("ALERT_TELEGRAM_CHAT_ID", "").strip()
    if tg_bot and tg_chat:
        sent = _send_telegram(tg_bot, tg_chat, message) or sent

    if sent:
        print("[OK] Gemini failure alert sent.")
    else:
        print("[WARN] Gemini failed but no alert channel configured (ALERT_WEBHOOK_URL or ALERT_TELEGRAM_*).")
