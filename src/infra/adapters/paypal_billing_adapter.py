"""HTTP adapter for PayPal subscription billing."""

import json
from decimal import Decimal
from typing import Any

import httpx

from src.domain.ports.paypal_billing_port import (
    PayPalSubscriptionSnapshot,
    PayPalWebhookVerification,
)
from src.infra.config.settings import Settings


class PayPalBillingAdapter:
    """PayPal REST API adapter with server-only credentials."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.settings.PAYPAL_API_BASE_URL.rstrip("/"),
            timeout=self.settings.PAYPAL_TIMEOUT_SECONDS,
        )

    async def _access_token(self) -> str:
        async with self._client() as client:
            response = await client.post(
                "/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(
                    self.settings.PAYPAL_CLIENT_ID,
                    self.settings.PAYPAL_CLIENT_SECRET,
                ),
            )
            response.raise_for_status()
            return str(response.json()["access_token"])

    async def get_subscription(
        self, subscription_id: str
    ) -> PayPalSubscriptionSnapshot:
        token = await self._access_token()
        async with self._client() as client:
            response = await client.get(
                f"/v1/billing/subscriptions/{subscription_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            payload = response.json()
        return self._subscription_snapshot(payload)

    async def verify_webhook(
        self, headers: dict[str, str], raw_body: bytes
    ) -> PayPalWebhookVerification:
        token = await self._access_token()
        event = json.loads(raw_body.decode("utf-8"))
        payload = {
            "auth_algo": headers.get("paypal-auth-algo")
            or headers.get("PAYPAL-AUTH-ALGO"),
            "cert_url": headers.get("paypal-cert-url")
            or headers.get("PAYPAL-CERT-URL"),
            "transmission_id": headers.get("paypal-transmission-id")
            or headers.get("PAYPAL-TRANSMISSION-ID"),
            "transmission_sig": headers.get("paypal-transmission-sig")
            or headers.get("PAYPAL-TRANSMISSION-SIG"),
            "transmission_time": headers.get("paypal-transmission-time")
            or headers.get("PAYPAL-TRANSMISSION-TIME"),
            "webhook_id": self.settings.PAYPAL_WEBHOOK_ID,
            "webhook_event": event,
        }
        async with self._client() as client:
            response = await client.post(
                "/v1/notifications/verify-webhook-signature",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            response.raise_for_status()
            verification = response.json()
        resource = event.get("resource") or {}
        event_type = event.get("event_type")
        return PayPalWebhookVerification(
            verified=verification.get("verification_status") == "SUCCESS",
            event_id=event.get("id"),
            event_type=event_type,
            resource_id=self._webhook_subscription_id(event_type, resource),
        )

    @staticmethod
    def _subscription_snapshot(payload: dict[str, Any]) -> PayPalSubscriptionSnapshot:
        billing_info = payload.get("billing_info") or {}
        last_payment = billing_info.get("last_payment") or {}
        amount = last_payment.get("amount") or {}
        amount_minor = None
        if amount.get("value") is not None:
            value = Decimal(str(amount["value"]))
            if value.as_tuple().exponent < -2:
                raise ValueError("PayPal amount has more than two decimal places")
            amount_minor = int(value * Decimal("100"))
        subscriber = payload.get("subscriber") or {}
        return PayPalSubscriptionSnapshot(
            id=str(payload.get("id")),
            plan_id=payload.get("plan_id"),
            custom_id=payload.get("custom_id"),
            status=payload.get("status"),
            merchant_id=(payload.get("payee") or {}).get("merchant_id"),
            subscriber_id=subscriber.get("payer_id"),
            currency=amount.get("currency_code"),
            amount_minor=amount_minor,
        )

    @staticmethod
    def _webhook_subscription_id(
        event_type: str | None, resource: dict[str, Any]
    ) -> str | None:
        if (event_type or "").startswith("PAYMENT.SALE."):
            return resource.get("billing_agreement_id") or resource.get("id")
        supplementary = resource.get("supplementary_data") or {}
        related = supplementary.get("related_ids") or {}
        return (
            related.get("subscription_id")
            or resource.get("billing_agreement_id")
            or resource.get("id")
        )
