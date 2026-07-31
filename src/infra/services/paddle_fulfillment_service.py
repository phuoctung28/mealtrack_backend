"""Verified Paddle webhook fulfillment using the shared subscription records."""

import json
import logging
import os
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions.paddle_billing_exceptions import PaddleWebhookRetryError
from src.domain.utils.timezone_utils import ensure_utc, utc_now
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User

logger = logging.getLogger(__name__)

HANDLED_EVENT_TYPES = {
    "subscription.created",
    "subscription.updated",
    "subscription.canceled",
    "customer.created",
    "customer.updated",
    "transaction.completed",
}


@dataclass(frozen=True)
class PaddleWebhookRequest:
    """Minimal request adapter consumed by Paddle's Python verifier."""

    body: bytes
    headers: Mapping[str, str]


def verify_paddle_webhook_signature(
    raw_body: bytes, headers: Mapping[str, str]
) -> bool:
    """Verify a webhook before decoding its unparsed request body."""
    secret = os.getenv("PADDLE_WEBHOOK_SIGNING_SECRET")
    if not secret:
        raise RuntimeError("PADDLE_WEBHOOK_SIGNING_SECRET must be set")

    from paddle_billing.Notifications import Secret, Verifier

    return bool(
        Verifier().verify(PaddleWebhookRequest(raw_body, headers), Secret(secret))
    )


async def process_verified_paddle_webhook(
    raw_body: bytes, session: AsyncSession
) -> dict[str, str]:
    """Route a signature-verified webhook to an idempotent persistence handler."""
    event = json.loads(raw_body.decode("utf-8"))
    event_id = _required_text(event, "event_id")
    event_type = _required_text(event, "event_type")

    if event_type not in HANDLED_EVENT_TYPES:
        logger.info("Ignoring verified Paddle event type %s", event_type)
        return {"status": "ignored", "event_type": event_type, "event_id": event_id}

    data = event.get("data") or {}
    if event_type.startswith("customer."):
        await _handle_customer(session, data)
    elif event_type.startswith("subscription."):
        await _handle_subscription(session, data)
    else:
        await _handle_transaction_completed(session, data)

    return {"status": "processed", "event_type": event_type, "event_id": event_id}


async def user_has_paddle_access(session: AsyncSession, user_id: str) -> bool:
    """Return whether an existing Paddle subscription currently grants access."""
    return await get_active_paddle_subscription(session, user_id) is not None


async def get_active_paddle_subscription(
    session: AsyncSession, user_id: str
) -> Subscription | None:
    """Return the first access-granting Paddle subscription for a user."""
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.provider == "paddle",
            Subscription.status.in_(("active", "trialing")),
        )
    )
    return next((item for item in result.scalars() if item.is_active()), None)


async def _handle_customer(session: AsyncSession, data: dict[str, object]) -> None:
    customer_id = _required_text(data, "id")
    email = _required_text(data, "email").lower()
    result = await session.execute(
        select(User.id).where(func.lower(User.email) == email)
    )
    user_id = result.scalar_one_or_none()
    if user_id is None:
        logger.info("Paddle customer %s has no matching application user", customer_id)
        return

    linked = await session.execute(
        update(User)
        .where(
            User.id == user_id,
            or_(
                User.paddle_customer_id.is_(None),
                User.paddle_customer_id == customer_id,
            ),
        )
        .values(paddle_customer_id=customer_id, updated_at=utc_now())
    )
    if not linked.rowcount:
        logger.warning("Refusing to replace Paddle customer link for user %s", user_id)
        return

    await session.execute(
        update(Subscription)
        .where(
            Subscription.provider == "paddle",
            Subscription.provider_customer_id == customer_id,
            Subscription.user_id.is_(None),
        )
        .values(user_id=str(user_id), updated_at=utc_now())
    )


async def _handle_subscription(session: AsyncSession, data: dict[str, object]) -> None:
    customer_id = _required_text(data, "customer_id")
    user_id = await _find_user_id_by_customer_id(session, customer_id)
    price_id, product_id = _extract_subscription_price(data)
    scheduled_change = data.get("scheduled_change") or {}
    if not isinstance(scheduled_change, dict):
        scheduled_change = {}
    updated_at = _parse_time(data.get("updated_at")) or utc_now()
    created_at = _parse_time(data.get("created_at")) or updated_at
    subscription_id = _required_text(data, "id")
    status = _required_text(data, "status")

    statement = insert(Subscription).values(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider="paddle",
        revenuecat_subscriber_id=None,
        provider_customer_id=customer_id,
        provider_subscription_id=subscription_id,
        status=status,
        price_id=price_id,
        product_id=product_id,
        platform="web",
        purchased_at=created_at,
        expires_at=_extract_period_end(data),
        cancelled_at=updated_at if status in {"canceled", "cancelled"} else None,
        scheduled_change_action=_optional_text(scheduled_change.get("action")),
        scheduled_change_at=_parse_time(
            scheduled_change.get("effective_at") or scheduled_change.get("resume_at")
        ),
        store_transaction_id=None,
        is_sandbox=False,
        created_at=created_at,
        updated_at=updated_at,
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=["provider_subscription_id"],
            set_={
                "user_id": func.coalesce(
                    Subscription.user_id, statement.excluded.user_id
                ),
                "provider_customer_id": customer_id,
                "status": status,
                "price_id": price_id,
                "product_id": product_id,
                "expires_at": _extract_period_end(data),
                "cancelled_at": updated_at
                if status in {"canceled", "cancelled"}
                else None,
                "scheduled_change_action": _optional_text(
                    scheduled_change.get("action")
                ),
                "scheduled_change_at": _parse_time(
                    scheduled_change.get("effective_at")
                    or scheduled_change.get("resume_at")
                ),
                "updated_at": updated_at,
            },
            where=Subscription.updated_at <= updated_at,
        )
    )


async def _handle_transaction_completed(
    session: AsyncSession, data: dict[str, object]
) -> None:
    """Attach the completed Paddle transaction to its already-mirrored subscription."""
    subscription_id = _optional_text(data.get("subscription_id"))
    if subscription_id is None:
        logger.info("Ignoring non-subscription Paddle transaction %s", data.get("id"))
        return

    price_id, product_id = _extract_transaction_price(data)
    updated = await session.execute(
        update(Subscription)
        .where(
            Subscription.provider == "paddle",
            Subscription.provider_subscription_id == subscription_id,
        )
        .values(
            store_transaction_id=_required_text(data, "id"),
            price_id=func.coalesce(price_id, Subscription.price_id),
            product_id=func.coalesce(product_id, Subscription.product_id),
            updated_at=_parse_time(data.get("updated_at")) or utc_now(),
        )
    )
    if not updated.rowcount:
        raise PaddleWebhookRetryError(
            f"Paddle subscription {subscription_id} has not been delivered yet"
        )


async def _find_user_id_by_customer_id(
    session: AsyncSession, customer_id: str
) -> str | None:
    result = await session.execute(
        select(User.id).where(User.paddle_customer_id == customer_id)
    )
    user_id = result.scalar_one_or_none()
    return str(user_id) if user_id else None


def _extract_subscription_price(data: dict[str, object]) -> tuple[str, str]:
    items = data.get("items") or [{}]
    first_item = items[0] if isinstance(items, list) and items else {}
    price = first_item.get("price") if isinstance(first_item, dict) else None
    return _required_text(price or {}, "id"), _required_text(price or {}, "product_id")


def _extract_transaction_price(
    data: dict[str, object],
) -> tuple[str | None, str | None]:
    details = data.get("details") or {}
    line_items = details.get("line_items") if isinstance(details, dict) else None
    first_item = line_items[0] if isinstance(line_items, list) and line_items else {}
    return _optional_text(first_item.get("price_id")), _optional_text(
        first_item.get("product_id")
    )


def _extract_period_end(data: dict[str, object]) -> datetime | None:
    period = data.get("current_billing_period") or {}
    return _parse_time(period.get("ends_at") if isinstance(period, dict) else None)


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _required_text(data: dict[str, object], key: str) -> str:
    value = _optional_text(data.get(key))
    if value is None:
        raise ValueError(f"Paddle payload missing required field: {key}")
    return value
