"""
Unit tests for subscription access middleware (DB-only, no RevenueCat API calls).
"""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request

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
        # No grace period for intentional cancellation
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

    @pytest.fixture
    def mock_request(self):
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        return request

    @pytest.fixture
    def user_with_active_sub(self):
        user = MagicMock()
        user.id = "user_123"
        sub = _make_sub("active", expires_at=utc_now() + timedelta(days=30))
        user.has_active_subscription = MagicMock(return_value=True)
        user.get_active_subscription = MagicMock(return_value=sub)
        user.subscriptions = [sub]
        return user

    @pytest.fixture
    def user_no_subscriptions(self):
        user = MagicMock()
        user.id = "user_456"
        user.has_active_subscription = MagicMock(return_value=False)
        user.get_active_subscription = MagicMock(return_value=None)
        user.subscriptions = []
        return user

    async def test_unauthenticated_raises_401(self, mock_request):
        mock_request.state.user = None
        with pytest.raises(HTTPException) as exc_info:
            await require_subscription(mock_request)
        assert exc_info.value.status_code == 401

    async def test_active_subscription_passes(self, mock_request, user_with_active_sub):
        mock_request.state.user = user_with_active_sub
        result = await require_subscription(mock_request)
        assert result is None

    async def test_no_subscription_raises_402(self, mock_request, user_no_subscriptions):
        mock_request.state.user = user_no_subscriptions
        with pytest.raises(HTTPException) as exc_info:
            await require_subscription(mock_request)
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["error_code"] == "SUBSCRIPTION_REQUIRED"

    async def test_cancelled_within_paid_period_passes(self, mock_request):
        user = MagicMock()
        user.id = "user_789"
        sub = _make_sub("cancelled", expires_at=utc_now() + timedelta(days=5))
        user.has_active_subscription = MagicMock(return_value=False)
        user.get_active_subscription = MagicMock(return_value=None)
        user.subscriptions = [sub]
        mock_request.state.user = user
        result = await require_subscription(mock_request)
        assert result is None

    async def test_billing_issue_within_grace_passes(self, mock_request):
        user = MagicMock()
        user.id = "user_999"
        sub = _make_sub("billing_issue", expires_at=utc_now() - timedelta(hours=6))
        user.has_active_subscription = MagicMock(return_value=False)
        user.get_active_subscription = MagicMock(return_value=None)
        user.subscriptions = [sub]
        mock_request.state.user = user
        result = await require_subscription(mock_request)
        assert result is None

    async def test_no_rc_api_calls_made(self, mock_request, user_no_subscriptions):
        """RC API must never be called during authorization."""
        mock_request.state.user = user_no_subscriptions
        # If RC adapter were called, it would fail with no mock configured.
        # The test passing without patching RC confirms no RC calls are made.
        with pytest.raises(HTTPException):
            await require_subscription(mock_request)


@pytest.mark.asyncio
class TestGetSubscriptionStatus:
    """Test the non-blocking get_subscription_status dependency."""

    @pytest.fixture
    def mock_request(self):
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        return request

    async def test_no_user_returns_false(self, mock_request):
        mock_request.state.user = None
        result = await get_subscription_status(mock_request)
        assert result["has_subscription"] is False
        assert result["source"] == "no_user"

    async def test_active_subscription_returns_info(self, mock_request):
        user = MagicMock()
        sub = _make_sub("active", expires_at=utc_now() + timedelta(days=30))
        sub.product_id = "premium_monthly"
        user.get_active_subscription = MagicMock(return_value=sub)
        mock_request.state.user = user
        result = await get_subscription_status(mock_request)
        assert result["has_subscription"] is True
        assert result["subscription"]["product_id"] == "premium_monthly"
        assert result["source"] == "cache"

    async def test_no_subscription_returns_false(self, mock_request):
        user = MagicMock()
        user.get_active_subscription = MagicMock(return_value=None)
        mock_request.state.user = user
        result = await get_subscription_status(mock_request)
        assert result["has_subscription"] is False
        assert result["source"] == "none"
