"""Rate limiting middleware using slowapi."""
from __future__ import annotations

import base64
import json

from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_id_or_ip(request):
    """Extract user ID from JWT payload for per-user limits, fallback to IP.

    Uses lightweight base64 decode of JWT payload (no verification).
    Auth is already enforced by verify_firebase_token dependency —
    this only needs a stable key for rate limiting.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            # Decode JWT payload without verification (just for rate limit key)
            payload_b64 = auth[7:].split(".")[1]
            # Add padding for base64
            padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            uid = payload.get("sub") or payload.get("uid")
            if uid:
                return uid
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_id_or_ip)
