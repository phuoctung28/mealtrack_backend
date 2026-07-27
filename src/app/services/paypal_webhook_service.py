"""Verified PayPal webhook processing."""

from fastapi import HTTPException, status

from src.app.services.web_funnel_checkout_service import PAYPAL_PROVIDER
from src.domain.ports.paypal_billing_port import PayPalBillingPort

PAYMENT_COMPLETED_EVENTS = {
    "PAYMENT.SALE.COMPLETED",
    "PAYMENT.CAPTURE.COMPLETED",
}
REVOKE_EVENTS = {
    "BILLING.SUBSCRIPTION.CANCELLED": "paypal_cancelled",
    "BILLING.SUBSCRIPTION.SUSPENDED": "paypal_suspended",
    "PAYMENT.SALE.REFUNDED": "paypal_refunded",
    "CUSTOMER.DISPUTE.CREATED": "paypal_dispute",
}


class PayPalWebhookService:
    """Processes PayPal webhooks only after provider signature verification."""

    def __init__(self, expected_merchant_id: str = "", signing_secret: str = ""):
        self.expected_merchant_id = expected_merchant_id
        self.signing_secret = signing_secret

    async def process(self, *, uow, paypal: PayPalBillingPort, headers, raw_body):
        verification = await paypal.verify_webhook(dict(headers), raw_body)
        if not verification.verified or not verification.event_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "INVALID_PAYPAL_SIGNATURE"},
            )

        checkout = None
        if verification.resource_id:
            checkout = await uow.web_funnel_checkouts.find_by_provider_subscription(
                PAYPAL_PROVIDER, verification.resource_id
            )

        event, inserted = await uow.web_funnel_checkouts.record_provider_event(
            provider=PAYPAL_PROVIDER,
            event_id=verification.event_id,
            event_type=verification.event_type or "UNKNOWN",
            provider_subscription_id=verification.resource_id,
            checkout_id=getattr(checkout, "id", None),
            verified=True,
            processing_result="stored",
        )
        if not inserted:
            return {"status": "ignored", "reason": "duplicate", "event_id": event.id}
        if not checkout:
            return {"status": "stored", "reason": "checkout_not_found"}

        snapshot = await paypal.get_subscription(checkout.provider_subscription_id)
        mismatch_reason = self._snapshot_mismatch_reason(checkout, snapshot)
        if mismatch_reason:
            return {"status": "ignored", "reason": mismatch_reason}

        event_type = verification.event_type or ""
        if event_type in PAYMENT_COMPLETED_EVENTS and snapshot.status == "ACTIVE":
            await uow.web_funnel_checkouts.mark_paid(checkout)
            return {"status": "success", "state": "paid_active"}
        if event_type in REVOKE_EVENTS:
            await uow.web_funnel_checkouts.mark_revoked(
                checkout, REVOKE_EVENTS[event_type]
            )
            return {"status": "success", "state": "revoked"}
        return {"status": "ignored", "reason": "non_entitling_event"}

    def _snapshot_mismatch_reason(self, checkout, snapshot) -> str | None:
        if snapshot.plan_id != checkout.provider_plan_id:
            return "plan_mismatch"
        if not self._custom_id_matches_checkout(snapshot.custom_id, checkout.id):
            return "custom_id_mismatch"
        if snapshot.currency and snapshot.currency != checkout.currency:
            return "currency_mismatch"
        if (
            snapshot.amount_minor is not None
            and snapshot.amount_minor != checkout.amount_minor
        ):
            return "amount_mismatch"
        if (
            self.expected_merchant_id
            and snapshot.merchant_id
            and snapshot.merchant_id != self.expected_merchant_id
        ):
            return "merchant_mismatch"
        return None

    def _custom_id_matches_checkout(self, custom_id: str | None, checkout_id: str) -> bool:
        if not custom_id or not self.signing_secret:
            return False
        import hashlib
        import hmac
        import json

        try:
            encoded, signature = custom_id.rsplit(".", 1)
            expected = hmac.new(
                self.signing_secret.encode("utf-8"),
                encoded.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return False
            payload = json.loads(encoded)
        except (ValueError, json.JSONDecodeError):
            return False
        return payload.get("checkout_id") == checkout_id
