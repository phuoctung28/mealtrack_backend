"""
Unit tests for subscription access middleware (DB-only, no RevenueCat API calls).
"""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.premium_check import (
    _has_subscription_access,
    require_subscription,
    get_subscription_status,
)
from src.domain.utils.timezone_utils import utc_now


def _make_sub(status, expires_at=None):
    sub = MagicMock()
    sub.status = status
    sub.expires_at = expires_at
    sub.product_id = "premium_monthly"
    sub.is_monthly = MagicMock(return_value=True)
    sub.is_yearly = MagicMock(return_value=False)
    return sub


def _mock_db_with_subscriptions(subscriptions):
    """Build an AsyncSession mock that returns the given subscriptions."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = subscriptions
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=mock_result)
    return db


class TestHasSubscriptionAccess:
    """Test the pure _has_subscription_access helper."""

    def test_no_subscriptions_denies(self):
        assert _has_subscription_access([], grace_period_hours=24) is False

    def test_active_lifetime_allows(self):
        sub = _make_sub("active", expires_at=None)
        assert _has_subscription_access([sub], grace_period_hours=24) is True

    def test_active_future_expiry_allows(self):
        sub = _make_sub("active", expires_at=utc_now() + timedelta(days=30))
        assert _has_subscription_access([sub], grace_period_hours=24) is True

    def test_active_within_grace_period_allows(self):
        sub = _make_sub("active", expires_at=utc_now() - timedelta(hours=12))
        assert _has_subscription_access([sub], grace_period_hours=24) is True

    def test_active_past_grace_period_denies(self):
        sub = _make_sub("active", expires_at=utc_now() - timedelta(hours=25))
        assert _has_subscription_access([sub], grace_period_hours=24) is False

    def test_cancelled_future_expiry_allows(self):
        sub = _make_sub("cancelled", expires_at=utc_now() + timedelta(days=10))
        assert _has_subscription_access([sub], grace_period_hours=24) is True

    def test_cancelled_past_expiry_denies_immediately(self):
        sub = _make_sub("cancelled", expires_at=utc_now() - timedelta(hours=1))
        assert _has_subscription_access([sub], grace_period_hours=24) is False

    def test_billing_issue_future_expiry_allows(self):
        sub = _make_sub("billing_issue", expires_at=utc_now() + timedelta(days=5))
        assert _has_subscription_access([sub], grace_period_hours=24) is True

    def test_billing_issue_within_grace_period_allows(self):
        sub = _make_sub("billing_issue", expires_at=utc_now() - timedelta(hours=12))
        assert _has_subscription_access([sub], grace_period_hours=24) is True

    def test_billing_issue_past_grace_period_denies(self):
        sub = _make_sub("billing_issue", expires_at=utc_now() - timedelta(hours=25))
        assert _has_subscription_access([sub], grace_period_hours=24) is False

    def test_refunded_always_denies(self):
        sub = _make_sub("refunded", expires_at=utc_now() + timedelta(days=30))
        assert _has_subscription_access([sub], grace_period_hours=24) is False

    def test_expired_always_denies(self):
        sub = _make_sub("expired", expires_at=utc_now() + timedelta(days=30))
        assert _has_subscription_access([sub], grace_period_hours=24) is False

    def test_one_valid_among_multiple_allows(self):
        expired_sub = _make_sub("expired", expires_at=utc_now() - timedelta(days=60))
        active_sub = _make_sub("active", expires_at=utc_now() + timedelta(days=30))
        assert _has_subscription_access([expired_sub, active_sub], grace_period_hours=24) is True

    def test_grace_period_zero_is_strict(self):
        sub = _make_sub("active", expires_at=utc_now() - timedelta(minutes=1))
        assert _has_subscription_access([sub], grace_period_hours=0) is False


@pytest.mark.asyncio
class TestRequireSubscription:
    """Test the require_subscription FastAPI dependency."""

    async def test_dev_environment_always_passes(self):
        """In dev mode, subscription check is bypassed entirely."""
        db = _mock_db_with_subscriptions([])
        with patch("src.api.middleware.premium_check.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "development"
            mock_settings.SUBSCRIPTION_GRACE_PERIOD_HOURS = 24
            result = await require_subscription(user_id="user_123", async_db=db)
        assert result is None
        db.execute.assert_not_called()

    async def test_active_subscription_passes(self):
        sub = _make_sub("active", expires_at=utc_now() + timedelta(days=30))
        db = _mock_db_with_subscriptions([sub])
        with patch("src.api.middleware.premium_check.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.SUBSCRIPTION_GRACE_PERIOD_HOURS = 24
            result = await require_subscription(user_id="user_123", async_db=db)
        assert result is None

    async def test_no_subscription_raises_402(self):
        db = _mock_db_with_subscriptions([])
        with patch("src.api.middleware.premium_check.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.SUBSCRIPTION_GRACE_PERIOD_HOURS = 24
            with pytest.raises(HTTPException) as exc_info:
                await require_subscription(user_id="user_456", async_db=db)
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["error_code"] == "SUBSCRIPTION_REQUIRED"

    async def test_cancelled_within_paid_period_passes(self):
        sub = _make_sub("cancelled", expires_at=utc_now() + timedelta(days=5))
        db = _mock_db_with_subscriptions([sub])
        with patch("src.api.middleware.premium_check.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.SUBSCRIPTION_GRACE_PERIOD_HOURS = 24
            result = await require_subscription(user_id="user_789", async_db=db)
        assert result is None

    async def test_billing_issue_within_grace_passes(self):
        sub = _make_sub("billing_issue", expires_at=utc_now() - timedelta(hours=6))
        db = _mock_db_with_subscriptions([sub])
        with patch("src.api.middleware.premium_check.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.SUBSCRIPTION_GRACE_PERIOD_HOURS = 24
            result = await require_subscription(user_id="user_999", async_db=db)
        assert result is None

    async def test_no_rc_api_calls_made(self):
        """RC API must never be called during authorization."""
        db = _mock_db_with_subscriptions([])
        with patch("src.api.middleware.premium_check.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.SUBSCRIPTION_GRACE_PERIOD_HOURS = 24
            with pytest.raises(HTTPException):
                await require_subscription(user_id="user_456", async_db=db)
        # If RC adapter were called, it would raise because it has no mock.
        # The test passing without patching RC confirms no RC calls are made.


@pytest.mark.asyncio
class TestGetSubscriptionStatus:
    """Test the non-blocking get_subscription_status dependency."""

    async def test_no_subscriptions_returns_false(self):
        db = _mock_db_with_subscriptions([])
        result = await get_subscription_status(user_id="user_123", async_db=db)
        assert result["has_subscription"] is False
        assert result["source"] == "db"

    async def test_active_subscription_returns_info(self):
        sub = _make_sub("active", expires_at=utc_now() + timedelta(days=30))
        sub.product_id = "premium_monthly"
        db = _mock_db_with_subscriptions([sub])
        result = await get_subscription_status(user_id="user_123", async_db=db)
        assert result["has_subscription"] is True
        assert result["subscription"]["product_id"] == "premium_monthly"
        assert result["source"] == "db"

    async def test_expired_subscription_returns_false(self):
        sub = _make_sub("expired", expires_at=utc_now() - timedelta(days=10))
        db = _mock_db_with_subscriptions([sub])
        result = await get_subscription_status(user_id="user_123", async_db=db)
        assert result["has_subscription"] is False
        assert result["source"] == "db"

    async def test_cancelled_within_paid_period_returns_true(self):
        sub = _make_sub("cancelled", expires_at=utc_now() + timedelta(days=5))
        db = _mock_db_with_subscriptions([sub])
        with patch("src.api.middleware.premium_check.settings") as mock_settings:
            mock_settings.SUBSCRIPTION_GRACE_PERIOD_HOURS = 24
            result = await get_subscription_status(user_id="user_123", async_db=db)
        assert result["has_subscription"] is True
        assert result["source"] == "db"

    async def test_billing_issue_within_grace_returns_true(self):
        sub = _make_sub("billing_issue", expires_at=utc_now() - timedelta(hours=6))
        db = _mock_db_with_subscriptions([sub])
        with patch("src.api.middleware.premium_check.settings") as mock_settings:
            mock_settings.SUBSCRIPTION_GRACE_PERIOD_HOURS = 24
            result = await get_subscription_status(user_id="user_123", async_db=db)
        assert result["has_subscription"] is True
        assert result["source"] == "db"
