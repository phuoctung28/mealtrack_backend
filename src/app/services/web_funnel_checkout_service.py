"""Application service for backend-owned web funnel checkouts."""

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status

from src.domain.ports.paypal_billing_port import (
    PayPalBillingPort,
    PayPalSubscriptionSnapshot,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.config.settings import Settings
from src.infra.database.models.web_funnel import WebFunnelCheckout

PAYPAL_PROVIDER = "paypal"
VN_COUNTRY = "VN"
WELCOME_REWARD_ID = "WELCOME50"
PAYMENT_COMPLETED_EVENTS = {
    "PAYMENT.SALE.COMPLETED",
    "PAYMENT.CAPTURE.COMPLETED",
}


@dataclass(frozen=True)
class OfferSnapshot:
    """Server-owned commercial snapshot for a funnel checkout."""

    offer_id: str
    reward_id: str
    market: str
    provider: str
    currency: str
    amount_minor: int
    renewal_interval: str
    plan_id: str
    welcome_discount_percent: int


class WebFunnelCheckoutService:
    """Coordinates checkout ledger creation, confirmation, and claims."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _require_secret(self) -> str:
        secret = self.settings.WEB_FUNNEL_SIGNING_SECRET
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "WEB_FUNNEL_NOT_CONFIGURED",
                    "message": "Web funnel checkout is not configured.",
                },
            )
        return secret

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _sign(self, payload: dict[str, Any]) -> str:
        secret = self._require_secret().encode("utf-8")
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        signature = hmac.new(secret, encoded.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def _verify_signed(self, signed_value: str) -> dict[str, Any]:
        try:
            encoded, signature = signed_value.rsplit(".", 1)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "INVALID_CUSTOM_ID"},
            ) from exc
        expected = hmac.new(
            self._require_secret().encode("utf-8"),
            encoded.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "INVALID_CUSTOM_ID"},
            )
        try:
            return json.loads(encoded)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "INVALID_CUSTOM_ID"},
            ) from exc

    def _request_fingerprint(
        self,
        *,
        lead_id: str,
        offer_id: str,
        reward_id: str,
        billing_country: str,
    ) -> str:
        return self._hash(
            json.dumps(
                {
                    "lead_id": lead_id,
                    "offer_id": offer_id,
                    "reward_id": reward_id,
                    "billing_country": billing_country.upper(),
                },
                sort_keys=True,
            )
        )

    def _select_offer(
        self, offer_id: str, reward_id: str, billing_country: str
    ) -> OfferSnapshot:
        country = billing_country.upper()
        if country == VN_COUNTRY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "PROVIDER_UNAVAILABLE",
                    "message": "Vietnam web checkout is unavailable.",
                },
            )
        if not self.settings.WEB_FUNNEL_CHECKOUT_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "WEB_FUNNEL_DISABLED",
                    "message": "Web funnel checkout is disabled.",
                },
            )

        offer = self.settings.web_funnel_paypal_offers.get(offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "UNKNOWN_OFFER"},
            )
        if offer.get("reward_id") != reward_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "OFFER_REWARD_MISMATCH"},
            )
        provider = str(offer.get("provider", PAYPAL_PROVIDER)).lower()
        currency = str(offer.get("currency", "USD")).upper()
        plan_id = str(offer.get("paypal_plan_id") or "")
        if provider != PAYPAL_PROVIDER or currency != "USD" or not plan_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error_code": "PROVIDER_UNAVAILABLE"},
            )
        return OfferSnapshot(
            offer_id=offer_id,
            reward_id=reward_id,
            market=str(offer.get("market", "INTL")),
            provider=provider,
            currency=currency,
            amount_minor=int(offer.get("amount_minor", 0)),
            renewal_interval=str(offer.get("renewal_interval", "monthly")),
            plan_id=plan_id,
            welcome_discount_percent=int(
                offer.get(
                    "welcome_discount_percent",
                    50 if reward_id == WELCOME_REWARD_ID else 0,
                )
            ),
        )

    def _snapshot_mismatch_reason(
        self, checkout: WebFunnelCheckout, snapshot: PayPalSubscriptionSnapshot
    ) -> str | None:
        if snapshot.plan_id != checkout.provider_plan_id:
            return "PLAN_MISMATCH"
        custom_payload = self._verify_signed(snapshot.custom_id or "")
        if custom_payload.get("checkout_id") != checkout.id:
            return "CUSTOM_ID_MISMATCH"
        if snapshot.currency and snapshot.currency != checkout.currency:
            return "CURRENCY_MISMATCH"
        if (
            snapshot.amount_minor is not None
            and snapshot.amount_minor != checkout.amount_minor
        ):
            return "AMOUNT_MISMATCH"
        expected_merchant = getattr(self.settings, "PAYPAL_MERCHANT_ID", "")
        if (
            expected_merchant
            and snapshot.merchant_id
            and snapshot.merchant_id != expected_merchant
        ):
            return "MERCHANT_MISMATCH"
        return None

    async def create_checkout(
        self,
        *,
        uow,
        lead_id: str,
        offer_id: str,
        reward_id: str,
        billing_country: str,
        idempotency_key: str,
    ) -> tuple[WebFunnelCheckout, str]:
        snapshot = self._select_offer(offer_id, reward_id, billing_country)
        lead = await uow.web_funnel_checkouts.get_or_create_lead(
            lead_id, billing_country.upper()
        )
        fingerprint = self._request_fingerprint(
            lead_id=lead_id,
            offer_id=offer_id,
            reward_id=reward_id,
            billing_country=billing_country,
        )
        idempotency_hash = self._hash(idempotency_key)
        existing = await uow.web_funnel_checkouts.find_by_lead_idempotency(
            lead.id, idempotency_hash
        )
        if existing:
            if existing.request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error_code": "IDEMPOTENCY_CONFLICT"},
                )
            custom_id = self._sign(
                {"checkout_id": existing.id, "provider": existing.provider}
            )
            return existing, custom_id

        checkout = WebFunnelCheckout(
            lead_id=lead.id,
            idempotency_key_hash=idempotency_hash,
            request_fingerprint=fingerprint,
            state="pending_approval",
            offer_id=snapshot.offer_id,
            reward_id=snapshot.reward_id,
            market=snapshot.market,
            billing_country=billing_country.upper(),
            provider=snapshot.provider,
            currency=snapshot.currency,
            amount_minor=snapshot.amount_minor,
            renewal_interval=snapshot.renewal_interval,
            welcome_discount_percent=snapshot.welcome_discount_percent,
            provider_plan_id=snapshot.plan_id,
            custom_id_hash=self._hash(secrets.token_urlsafe(32)),
            claim_token_hash=self._hash(secrets.token_urlsafe(32)),
            claim_expires_at=utc_now()
            + timedelta(minutes=self.settings.WEB_FUNNEL_CLAIM_TOKEN_TTL_MINUTES),
        )
        await uow.web_funnel_checkouts.add_checkout(checkout)
        if checkout.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "IDEMPOTENCY_CONFLICT"},
            )
        custom_id = self._sign({"checkout_id": checkout.id, "provider": snapshot.provider})
        checkout.custom_id_hash = self._hash(custom_id)
        checkout.claim_token_hash = self._hash(self.claim_token_for_checkout(checkout))
        await uow.session.flush()
        return checkout, custom_id

    def claim_token_for_checkout(self, checkout: WebFunnelCheckout) -> str:
        return self._sign({"checkout_id": checkout.id, "purpose": "claim"})

    async def confirm_paypal_subscription(
        self,
        *,
        uow,
        paypal: PayPalBillingPort,
        checkout_id: str,
        subscription_id: str,
    ) -> WebFunnelCheckout:
        checkout = await uow.web_funnel_checkouts.find_by_id(checkout_id)
        if not checkout:
            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND"})
        if checkout.state not in {"pending_approval", "pending_payment"}:
            raise HTTPException(
                status_code=409, detail={"error_code": "CHECKOUT_NOT_CONFIRMABLE"}
            )
        if checkout.provider != PAYPAL_PROVIDER or not checkout.provider_plan_id:
            raise HTTPException(
                status_code=400, detail={"error_code": "PROVIDER_UNAVAILABLE"}
            )
        if checkout.provider_subscription_id:
            if checkout.provider_subscription_id != subscription_id:
                raise HTTPException(
                    status_code=409,
                    detail={"error_code": "SUBSCRIPTION_ALREADY_BOUND"},
                )
            return checkout

        snapshot = await paypal.get_subscription(subscription_id)
        mismatch_reason = self._snapshot_mismatch_reason(checkout, snapshot)
        if mismatch_reason:
            raise HTTPException(
                status_code=400, detail={"error_code": mismatch_reason}
            )
        await uow.web_funnel_checkouts.record_confirmation(
            checkout, subscription_id
        )
        await self._apply_early_verified_payment_if_present(
            uow=uow, checkout=checkout, snapshot=snapshot
        )
        return checkout

    async def validate_paypal_subscription(
        self,
        *,
        uow,
        checkout_id: str,
        subscription_id: str,
        snapshot: PayPalSubscriptionSnapshot,
    ) -> WebFunnelCheckout:
        checkout = await uow.web_funnel_checkouts.find_by_id(checkout_id)
        if not checkout:
            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND"})
        if checkout.state not in {"pending_approval", "pending_payment"}:
            raise HTTPException(
                status_code=409, detail={"error_code": "CHECKOUT_NOT_CONFIRMABLE"}
            )
        if checkout.provider_subscription_id:
            if checkout.provider_subscription_id != subscription_id:
                raise HTTPException(
                    status_code=409,
                    detail={"error_code": "SUBSCRIPTION_ALREADY_BOUND"},
                )
            return checkout
        mismatch_reason = self._snapshot_mismatch_reason(checkout, snapshot)
        if mismatch_reason:
            raise HTTPException(
                status_code=400, detail={"error_code": mismatch_reason}
            )
        return checkout

    async def bind_validated_paypal_subscription(
        self,
        *,
        uow,
        checkout_id: str,
        subscription_id: str,
        snapshot: PayPalSubscriptionSnapshot,
    ) -> WebFunnelCheckout:
        checkout = await uow.web_funnel_checkouts.find_by_id(checkout_id)
        if not checkout:
            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND"})
        if checkout.provider_subscription_id:
            if checkout.provider_subscription_id != subscription_id:
                raise HTTPException(
                    status_code=409,
                    detail={"error_code": "SUBSCRIPTION_ALREADY_BOUND"},
                )
            return checkout
        mismatch_reason = self._snapshot_mismatch_reason(checkout, snapshot)
        if mismatch_reason:
            raise HTTPException(
                status_code=400, detail={"error_code": mismatch_reason}
            )
        bound = await uow.web_funnel_checkouts.record_confirmation(
            checkout, subscription_id
        )
        if bound.id != checkout.id:
            raise HTTPException(
                status_code=409,
                detail={"error_code": "SUBSCRIPTION_ALREADY_BOUND"},
            )
        checkout = bound
        await self._apply_early_verified_payment_if_present(
            uow=uow, checkout=checkout, snapshot=snapshot
        )
        return checkout

    async def _apply_early_verified_payment_if_present(
        self,
        *,
        uow,
        checkout: WebFunnelCheckout,
        snapshot: PayPalSubscriptionSnapshot,
    ) -> None:
        if snapshot.status != "ACTIVE":
            return
        event = await uow.web_funnel_checkouts.find_latest_verified_event_for_subscription(
            PAYPAL_PROVIDER,
            checkout.provider_subscription_id,
            PAYMENT_COMPLETED_EVENTS,
        )
        if event:
            await uow.web_funnel_checkouts.mark_paid(checkout)

    async def claim_checkout(self, *, uow, user_id: str, claim_token: str):
        checkout = await uow.web_funnel_checkouts.find_by_claim_hash(
            self._hash(claim_token)
        )
        if not checkout or checkout.claim_expires_at < utc_now():
            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND"})
        if checkout.state != "paid_active" or not checkout.provider_subscription_id:
            raise HTTPException(
                status_code=409, detail={"error_code": "CHECKOUT_NOT_CLAIMABLE"}
            )
        if checkout.claimed_at:
            raise HTTPException(
                status_code=409, detail={"error_code": "CHECKOUT_ALREADY_CLAIMED"}
            )
        try:
            return await uow.web_funnel_checkouts.claim_checkout(checkout, user_id)
        except ValueError as exc:
            error_code = str(exc).upper()
            raise HTTPException(status_code=409, detail={"error_code": error_code}) from exc
