"""HTTP helpers with retry logic."""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request


def urlopen_with_retry(
    req: urllib.request.Request,
    timeout_sec: int,
    label: str,
):
    retries = max(1, int(os.getenv("HTTP_RETRIES", "3")))
    backoff_sec = max(1, int(os.getenv("HTTP_RETRY_BACKOFF_SEC", "2")))
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout_sec)
        except Exception as exc:
            last_exc = exc
            reason = exc
            if isinstance(exc, urllib.error.URLError):
                reason = exc.reason
            print(f"[WARN] {label} failed ({attempt}/{retries}): {reason}")
            if attempt < retries:
                time.sleep(backoff_sec * attempt)

    if last_exc is not None:
        raise last_exc

    raise RuntimeError(f"{label} failed unexpectedly")
