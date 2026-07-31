"""Infrastructure implementation of the Paddle billing application port."""

import asyncio
from collections.abc import Mapping

from sqlalchemy import select

from src.domain.exceptions.paddle_billing_exceptions import PaddleCustomerNotFoundError
from src.domain.model.paddle_billing import PaddleSubscriptionStatus
from src.domain.ports.paddle_billing_port import PaddleBillingPort
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.paddle_client import build_paddle_client
from src.infra.services.paddle_fulfillment_service import (
    get_active_paddle_subscription,
    process_verified_paddle_webhook,
    user_has_paddle_access,
    verify_paddle_webhook_signature,
)


class PaddleBillingGateway(PaddleBillingPort):
    """Executes Paddle SDK calls and database work behind an application port."""

    def verify_webhook_signature(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> bool:
        return verify_paddle_webhook_signature(raw_body, headers)

    async def process_webhook(self, raw_body: bytes) -> dict[str, str]:
        async with AsyncUnitOfWork() as uow:
            if uow.session is None:
                raise RuntimeError("Database session was not initialized")
            return await process_verified_paddle_webhook(raw_body, uow.session)

    async def user_has_access(self, user_id: str) -> bool:
        async with AsyncUnitOfWork() as uow:
            if uow.session is None:
                return False
            return await user_has_paddle_access(uow.session, user_id)

    async def get_active_subscription(
        self, user_id: str
    ) -> PaddleSubscriptionStatus | None:
        async with AsyncUnitOfWork() as uow:
            if uow.session is None:
                return None
            subscription = await get_active_paddle_subscription(uow.session, user_id)
        if subscription is None:
            return None
        return PaddleSubscriptionStatus(
            product_id=subscription.product_id,
            price_id=subscription.price_id,
            status=subscription.status,
            expires_at=subscription.expires_at,
        )

    async def create_customer_portal_url(self, user_id: str) -> str:
        async with AsyncUnitOfWork() as uow:
            if uow.session is None:
                raise RuntimeError("Database session was not initialized")
            customer_id = await uow.session.scalar(
                select(User.paddle_customer_id).where(User.id == user_id)
            )
            if customer_id is None:
                raise PaddleCustomerNotFoundError(
                    "No Paddle customer is linked to this account"
                )
            result = await uow.session.execute(
                select(Subscription.provider_subscription_id)
                .where(
                    Subscription.user_id == user_id,
                    Subscription.provider == "paddle",
                )
                .order_by(Subscription.updated_at.desc())
                .limit(25)
            )
            subscription_ids = list(result.scalars())

        return await asyncio.to_thread(
            _create_customer_portal_session, customer_id, subscription_ids
        )


def _create_customer_portal_session(
    customer_id: str, subscription_ids: list[str]
) -> str:
    from paddle_billing.Resources.CustomerPortalSessions.Operations import (
        CreateCustomerPortalSession,
    )

    operation = (
        CreateCustomerPortalSession(subscription_ids=subscription_ids)
        if subscription_ids
        else CreateCustomerPortalSession()
    )
    session = build_paddle_client().customer_portal_sessions.create(
        customer_id, operation
    )
    return session.urls.general.overview
