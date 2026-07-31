"""Paddle access-state tests."""

from datetime import timedelta

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.subscription import Subscription


def _subscription(status: str, ends_in_days: int | None = 30) -> Subscription:
    period_end = None
    if ends_in_days is not None:
        period_end = utc_now() + timedelta(days=ends_in_days)
    return Subscription(
        provider="paddle",
        provider_subscription_id="sub_test",
        provider_customer_id="ctm_test",
        status=status,
        price_id="pri_test",
        product_id="pro_test",
        platform="web",
        purchased_at=utc_now(),
        expires_at=period_end,
    )


def test_active_subscription_grants_access_with_scheduled_cancellation():
    subscription = _subscription("active")
    subscription.scheduled_change_action = "cancel"

    assert subscription.is_active() is True


def test_trialing_subscription_grants_access():
    assert _subscription("trialing").is_active() is True


def test_canceled_paused_and_past_due_subscriptions_do_not_grant_access():
    assert _subscription("canceled").is_active() is False
    assert _subscription("paused").is_active() is False
    assert _subscription("past_due").is_active() is False


def test_expired_active_subscription_does_not_grant_access():
    assert _subscription("active", ends_in_days=-1).is_active() is False
