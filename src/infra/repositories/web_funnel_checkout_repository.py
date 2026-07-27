"""Repository for web funnel checkout ledger state."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User
from src.infra.database.models.web_funnel import (
    WebFunnelCheckout,
    WebFunnelClaim,
    WebFunnelLead,
    WebFunnelProviderEvent,
)


class WebFunnelCheckoutRepository:
    """Async repository for web funnel checkout records. Never commits."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_lead(
        self, external_lead_id: str, billing_country: str
    ) -> WebFunnelLead:
        result = await self.session.execute(
            select(WebFunnelLead).where(
                WebFunnelLead.external_lead_id == external_lead_id
            )
        )
        lead = result.scalars().first()
        if lead:
            lead.last_seen_country = billing_country
            return lead

        lead = WebFunnelLead(
            external_lead_id=external_lead_id,
            first_seen_country=billing_country,
            last_seen_country=billing_country,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(lead)
                await self.session.flush()
            return lead
        except IntegrityError:
            result = await self.session.execute(
                select(WebFunnelLead).where(
                    WebFunnelLead.external_lead_id == external_lead_id
                )
            )
            lead = result.scalars().first()
            if lead is None:
                raise
            lead.last_seen_country = billing_country
            return lead

    async def find_by_id(self, checkout_id: str) -> WebFunnelCheckout | None:
        result = await self.session.execute(
            select(WebFunnelCheckout).where(WebFunnelCheckout.id == checkout_id)
        )
        return result.scalars().first()

    async def find_by_custom_hash(
        self, custom_id_hash: str
    ) -> WebFunnelCheckout | None:
        result = await self.session.execute(
            select(WebFunnelCheckout).where(
                WebFunnelCheckout.custom_id_hash == custom_id_hash
            )
        )
        return result.scalars().first()

    async def find_by_claim_hash(
        self, claim_token_hash: str
    ) -> WebFunnelCheckout | None:
        result = await self.session.execute(
            select(WebFunnelCheckout).where(
                WebFunnelCheckout.claim_token_hash == claim_token_hash
            )
        )
        return result.scalars().first()

    async def find_by_provider_subscription(
        self, provider: str, provider_subscription_id: str
    ) -> WebFunnelCheckout | None:
        result = await self.session.execute(
            select(WebFunnelCheckout).where(
                WebFunnelCheckout.provider == provider,
                WebFunnelCheckout.provider_subscription_id
                == provider_subscription_id,
            )
        )
        return result.scalars().first()

    async def find_by_lead_idempotency(
        self, lead_id: str, idempotency_key_hash: str
    ) -> WebFunnelCheckout | None:
        result = await self.session.execute(
            select(WebFunnelCheckout).where(
                WebFunnelCheckout.lead_id == lead_id,
                WebFunnelCheckout.idempotency_key_hash == idempotency_key_hash,
            )
        )
        return result.scalars().first()

    async def add_checkout(
        self, checkout: WebFunnelCheckout
    ) -> WebFunnelCheckout:
        try:
            async with self.session.begin_nested():
                self.session.add(checkout)
                await self.session.flush()
            return checkout
        except IntegrityError:
            existing = await self.find_by_lead_idempotency(
                checkout.lead_id, checkout.idempotency_key_hash
            )
            if existing:
                return existing
            raise

    async def record_confirmation(
        self, checkout: WebFunnelCheckout, subscription_id: str
    ) -> WebFunnelCheckout:
        try:
            async with self.session.begin_nested():
                checkout.provider_subscription_id = subscription_id
                checkout.confirmed_at = checkout.confirmed_at or utc_now()
                if checkout.state == "pending_approval":
                    checkout.state = "pending_payment"
                await self.session.flush()
            return checkout
        except IntegrityError:
            existing = await self.find_by_provider_subscription(
                checkout.provider, subscription_id
            )
            if existing:
                return existing
            raise

    async def record_provider_event(
        self,
        provider: str,
        event_id: str,
        event_type: str,
        provider_subscription_id: str | None,
        checkout_id: str | None,
        verified: bool,
        processing_result: str,
    ) -> tuple[WebFunnelProviderEvent, bool]:
        result = await self.session.execute(
            select(WebFunnelProviderEvent).where(
                WebFunnelProviderEvent.provider == provider,
                WebFunnelProviderEvent.event_id == event_id,
            )
        )
        existing = result.scalars().first()
        if existing:
            return existing, False

        event = WebFunnelProviderEvent(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            provider_subscription_id=provider_subscription_id,
            checkout_id=checkout_id,
            verified=verified,
            processed=True,
            processing_result=processing_result,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(event)
                await self.session.flush()
            return event, True
        except IntegrityError:
            result = await self.session.execute(
                select(WebFunnelProviderEvent).where(
                    WebFunnelProviderEvent.provider == provider,
                    WebFunnelProviderEvent.event_id == event_id,
                )
            )
            existing = result.scalars().first()
            if existing:
                return existing, False
            raise

    async def find_latest_verified_event_for_subscription(
        self, provider: str, provider_subscription_id: str, event_types: set[str]
    ) -> WebFunnelProviderEvent | None:
        result = await self.session.execute(
            select(WebFunnelProviderEvent)
            .where(
                WebFunnelProviderEvent.provider == provider,
                WebFunnelProviderEvent.provider_subscription_id
                == provider_subscription_id,
                WebFunnelProviderEvent.verified.is_(True),
                WebFunnelProviderEvent.event_type.in_(event_types),
            )
            .order_by(WebFunnelProviderEvent.created_at.desc())
        )
        return result.scalars().first()

    async def mark_paid(
        self, checkout: WebFunnelCheckout, paid_at: datetime | None = None
    ) -> WebFunnelCheckout:
        checkout.state = "paid_active"
        checkout.state_reason = "paypal_verified_active"
        checkout.paid_at = paid_at or utc_now()
        await self.session.flush()
        return checkout

    async def mark_revoked(
        self, checkout: WebFunnelCheckout, reason: str
    ) -> WebFunnelCheckout:
        checkout.state = "revoked"
        checkout.state_reason = reason
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.provider == checkout.provider,
                Subscription.provider_subscription_id
                == checkout.provider_subscription_id,
            )
        )
        subscription = result.scalars().first()
        if subscription:
            subscription.status = (
                "refunded" if "refund" in reason or "dispute" in reason else "cancelled"
            )
            subscription.updated_at = utc_now()
        await self.session.flush()
        return checkout

    async def claim_checkout(
        self, checkout: WebFunnelCheckout, user_id: str
    ) -> Subscription:
        now = utc_now()
        result = await self.session.execute(
            select(WebFunnelCheckout)
            .where(WebFunnelCheckout.id == checkout.id)
            .with_for_update()
        )
        locked_checkout = result.scalars().first()
        if locked_checkout is None:
            raise ValueError("checkout_not_found")
        checkout = locked_checkout
        if checkout.claimed_at or checkout.state == "claimed":
            result = await self.session.execute(
                select(Subscription).where(Subscription.source_checkout_id == checkout.id)
            )
            existing = result.scalars().first()
            if existing:
                return existing
            raise ValueError("checkout_already_claimed")
        if checkout.state != "paid_active":
            raise ValueError("checkout_not_claimable")

        checkout.state = "claimed"
        checkout.claimed_at = now
        claim = WebFunnelClaim(
            checkout_id=checkout.id,
            user_id=user_id,
            claim_token_hash=checkout.claim_token_hash,
            claimed_at=now,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(claim)
                await self.session.flush()
        except IntegrityError:
            checkout = await self.find_by_id(checkout.id)
            if checkout and checkout.claimed_at:
                result = await self.session.execute(
                    select(Subscription).where(
                        Subscription.source_checkout_id == checkout.id
                    )
                )
                existing = result.scalars().first()
                if existing:
                    return existing
            raise

        result = await self.session.execute(
            select(Subscription).where(
                Subscription.provider == checkout.provider,
                Subscription.provider_subscription_id
                == checkout.provider_subscription_id,
            )
        )
        subscription = result.scalars().first()
        if subscription is None:
            subscription = Subscription(
                user_id=user_id,
                revenuecat_subscriber_id=None,
                provider=checkout.provider,
                provider_customer_id=checkout.provider_customer_id,
                provider_subscription_id=checkout.provider_subscription_id,
                provider_transaction_id=checkout.provider_transaction_id,
                source_checkout_id=checkout.id,
                product_id=checkout.offer_id,
                platform="web",
                status="active",
                purchased_at=checkout.paid_at or now,
                expires_at=None,
                store_transaction_id=checkout.provider_transaction_id,
                is_sandbox=False,
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(subscription)
                    await self.session.flush()
            except IntegrityError:
                result = await self.session.execute(
                    select(Subscription).where(
                        Subscription.provider == checkout.provider,
                        Subscription.provider_subscription_id
                        == checkout.provider_subscription_id,
                    )
                )
                subscription = result.scalars().first()
                if subscription is None:
                    raise
        else:
            subscription.user_id = user_id
            subscription.status = "active"
            subscription.source_checkout_id = checkout.id

        await self.session.flush()
        return subscription

    async def find_user_by_id(self, user_id: str) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()
