"""httpx adapter for nutree-affiliate internal API with HMAC-SHA256 request signing."""
import hashlib
import hmac
import json
import logging
import time
import uuid

import httpx

from src.domain.ports.affiliate_service_port import (
    AffiliateCodeValidationResult,
    AffiliateServicePort,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.config.settings import settings

logger = logging.getLogger(__name__)


def _sign_request(raw_body: str, timestamp: str, secret: str) -> str:
    """Produce HMAC-SHA256 hex digest matching nutree-affiliate signature.ts."""
    message = f"{timestamp}.{raw_body}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


class AffiliateServiceAdapter(AffiliateServicePort):
    async def validate_code(self, code: str) -> AffiliateCodeValidationResult:
        base_url = settings.AFFILIATE_API_BASE_URL
        secret = settings.AFFILIATE_INTERNAL_SECRET
        if not base_url or not secret:
            logger.warning("Affiliate integration not configured — skipping validation")
            return AffiliateCodeValidationResult(active=False)

        body = json.dumps({"code": code}, separators=(",", ":"))
        timestamp = str(int(time.time()))
        signature = _sign_request(body, timestamp, secret)

        url = f"{base_url.rstrip('/')}/api/internal/codes/validate"
        headers = {
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }

        try:
            async with httpx.AsyncClient(
                timeout=settings.AFFILIATE_CODE_VALIDATE_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(url, content=body, headers=headers)
        except httpx.TimeoutException:
            logger.warning("Affiliate code validation timed out for code=%s", code)
            return AffiliateCodeValidationResult(active=False)
        except httpx.HTTPError as exc:
            logger.warning("Affiliate code validation HTTP error: %s", exc)
            return AffiliateCodeValidationResult(active=False)

        if resp.status_code != 200:
            logger.warning(
                "Affiliate validation returned %s for code=%s", resp.status_code, code
            )
            return AffiliateCodeValidationResult(active=False)

        data = resp.json()
        if not data.get("active"):
            return AffiliateCodeValidationResult(active=False)

        return AffiliateCodeValidationResult(
            active=True,
            affiliate_id=data.get("affiliateId"),
            code_id=data.get("codeId"),
            display_name=data.get("displayName"),
            partner_type=data.get("partnerType"),
        )

    async def send_event(self, payload: dict) -> bool:
        """POST a signed event to nutree-affiliate mealtrack-events endpoint.

        Returns True on success or duplicate (idempotent). Returns False on
        transient error — callers should log and continue rather than hard-fail.
        """
        base_url = settings.AFFILIATE_API_BASE_URL
        secret = settings.AFFILIATE_INTERNAL_SECRET
        if not base_url or not secret:
            logger.warning("Affiliate integration not configured — cannot send event")
            return False

        if "event_id" not in payload:
            payload = {**payload, "event_id": str(uuid.uuid4())}
        if "occurred_at" not in payload:
            payload = {**payload, "occurred_at": utc_now().isoformat()}

        body = json.dumps(payload, separators=(",", ":"))
        timestamp = str(int(time.time()))
        signature = _sign_request(body, timestamp, secret)

        url = f"{base_url.rstrip('/')}/api/internal/mealtrack-events"
        headers = {
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }

        try:
            async with httpx.AsyncClient(
                timeout=settings.AFFILIATE_CODE_VALIDATE_TIMEOUT_SECONDS
            ) as client:
                resp = await client.post(url, content=body, headers=headers)
        except httpx.TimeoutException:
            logger.warning("Affiliate event send timed out: event_type=%s", payload.get("event_type"))
            return False
        except httpx.HTTPError as exc:
            logger.warning("Affiliate event send HTTP error: %s", exc)
            return False

        if resp.status_code == 200:
            return True

        logger.warning(
            "Affiliate event send returned %s: event_type=%s",
            resp.status_code, payload.get("event_type"),
        )
        return False
