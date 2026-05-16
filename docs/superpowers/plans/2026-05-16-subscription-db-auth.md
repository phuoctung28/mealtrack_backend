# Subscription DB-as-Auth-Source-of-Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local PostgreSQL database the sole source of truth for subscription authorization — no live RevenueCat API calls during request auth.

**Architecture:** `require_subscription` (FastAPI Depends) is rewritten to check `user.subscriptions` directly with configurable grace period logic. RC webhooks continue to write subscription state to the DB. Gated routers in `main.py` receive `dependencies=[Depends(require_subscription)]`.

**Tech Stack:** FastAPI Depends, SQLAlchemy ORM (subscriptions eagerly loaded via `selectinload`), Pydantic Settings, pytest-asyncio

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/infra/config/settings.py` | Modify | Add `SUBSCRIPTION_GRACE_PERIOD_HOURS` |
| `.env.example` | Modify | Document new env var |
| `src/api/middleware/premium_check.py` | Modify | Rewrite to DB-only with grace period |
| `src/api/main.py` | Modify | Apply `Depends(require_subscription)` to gated routers |
| `tests/unit/api/test_premium_middleware.py` | Modify | Replace RC-fallback tests with DB-only grace period tests |

---

## Task 1: Add Grace Period Setting

**Files:**
- Modify: `src/infra/config/settings.py:119-121`
- Modify: `.env.example:118-119`

- [ ] **Step 1: Add setting to Settings class**

In `src/infra/config/settings.py`, after line 120 (`REVENUECAT_WEBHOOK_SECRET`):

```python
    REVENUECAT_SECRET_API_KEY: str | None = Field(default=None)
    REVENUECAT_WEBHOOK_SECRET: str | None = Field(default=None)
    SUBSCRIPTION_GRACE_PERIOD_HOURS: int = Field(
        default=24,
        description="Hours past expires_at before denying access (buffer for webhook delays and billing retries)",
    )
```

- [ ] **Step 2: Add to .env.example**

In `.env.example`, after line 119 (`REVENUECAT_WEBHOOK_SECRET=`):

```
REVENUECAT_SECRET_API_KEY=
REVENUECAT_WEBHOOK_SECRET=
SUBSCRIPTION_GRACE_PERIOD_HOURS=24
```

- [ ] **Step 3: Commit**

```bash
git add src/infra/config/settings.py .env.example
git commit -m "feat(subscription): add SUBSCRIPTION_GRACE_PERIOD_HOURS setting"
```

---

## Task 2: Rewrite `require_subscription` (TDD)

**Files:**
- Modify: `tests/unit/api/test_premium_middleware.py` (replace all existing tests)
- Modify: `src/api/middleware/premium_check.py`

- [ ] **Step 1: Replace test file with failing tests**

Replace the entire content of `tests/unit/api/test_premium_middleware.py` with:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3.11 -m pytest tests/unit/api/test_premium_middleware.py -v 2>&1 | tail -20
```

Expected: `ImportError` — `_has_subscription_access` not yet exported from `premium_check.py`

- [ ] **Step 3: Rewrite premium_check.py**

Replace the entire content of `src/api/middleware/premium_check.py` with:

```python
"""
Subscription access validation middleware.

Uses the local database as the sole source of truth.
RevenueCat webhooks keep the DB in sync; no live RC API calls are made here.
"""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import Request, HTTPException, status

from src.domain.utils.timezone_utils import utc_now
from src.infra.config.settings import settings

logger = logging.getLogger(__name__)


def _has_subscription_access(subscriptions, grace_period_hours: int) -> bool:
    """
    Return True if any subscription in the list grants access.

    Grace period tolerates webhook delivery delays and billing retry windows.
    Intentionally cancelled subscriptions get no grace period — access ends at expires_at.
    """
    now = utc_now()
    grace = timedelta(hours=grace_period_hours)

    for sub in subscriptions:
        if sub.status in ("refunded", "expired"):
            continue

        if sub.status == "active":
            if sub.expires_at is None:
                return True  # Lifetime subscription
            if now <= sub.expires_at + grace:
                return True

        elif sub.status == "cancelled":
            # No grace period — user intentionally cancelled
            if sub.expires_at and now <= sub.expires_at:
                return True

        elif sub.status == "billing_issue":
            # Grace period covers the billing retry window
            if sub.expires_at and now <= sub.expires_at + grace:
                return True

    return False


async def require_subscription(request: Request):
    """
    FastAPI dependency that requires an active subscription.

    Checks the local database only. No RevenueCat API calls.

    Usage:
        router = APIRouter(dependencies=[Depends(require_subscription)])
    """
    user = getattr(request.state, "user", None)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Fast path: covers active subscriptions and the dev mock (has_active_subscription=lambda: True)
    if user.has_active_subscription():
        return

    # Grace period path: covers cancelled-within-period and billing_issue cases
    subscriptions = getattr(user, "subscriptions", [])
    if _has_subscription_access(subscriptions, settings.SUBSCRIPTION_GRACE_PERIOD_HOURS):
        logger.debug(f"User {user.id} allowed via grace period / paid-through-period check")
        return

    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "message": "Standard subscription required",
            "error_code": "SUBSCRIPTION_REQUIRED",
        },
    )


async def get_subscription_status(request: Request) -> dict:
    """
    Non-blocking subscription check that returns status info.

    Usage:
        @router.get("/feature")
        async def feature(status_info: dict = Depends(get_subscription_status)):
            if status_info["has_subscription"]:
                return {"data": "premium content"}
    """
    user = getattr(request.state, "user", None)

    if not user:
        return {"has_subscription": False, "subscription": None, "source": "no_user"}

    subscription = user.get_active_subscription()

    if subscription:
        return {
            "has_subscription": True,
            "subscription": {
                "product_id": subscription.product_id,
                "expires_at": (
                    subscription.expires_at.isoformat()
                    if subscription.expires_at
                    else None
                ),
                "is_monthly": subscription.is_monthly(),
                "is_yearly": subscription.is_yearly(),
            },
            "source": "cache",
        }

    return {"has_subscription": False, "subscription": None, "source": "none"}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3.11 -m pytest tests/unit/api/test_premium_middleware.py -v 2>&1 | tail -30
```

Expected: All tests pass. No RC-related test names in output.

- [ ] **Step 5: Run full unit suite to check for regressions**

```bash
python3.11 -m pytest tests/unit/ -q --tb=short --ignore=tests/unit/api/middleware/test_rate_limit.py --ignore=tests/unit/api/test_meal_suggestions_routes.py --ignore=tests/unit/domain/test_feature_flags.py --ignore=tests/unit/infra/adapters/test_deepl_translation_adapter.py 2>&1 | tail -10
```

Expected: Same pass count as baseline (1140), no new failures.

- [ ] **Step 6: Commit**

```bash
git add src/api/middleware/premium_check.py tests/unit/api/test_premium_middleware.py
git commit -m "feat(subscription): rewrite require_subscription to DB-only with grace period"
```

---

## Task 3: Gate Premium Routers in main.py

**Files:**
- Modify: `src/api/main.py:34-35,239-258`

- [ ] **Step 1: Add import and apply dependencies to gated routers**

In `src/api/main.py`, add the import after the existing middleware imports (around line 40):

```python
from src.api.middleware.premium_check import require_subscription
from fastapi import Depends
```

Then replace the router include block (lines 239–258) with:

```python
_sub = [Depends(require_subscription)]

# Public routes — no subscription required
app.include_router(health_router)
app.include_router(users_router)
app.include_router(webhooks_router)
app.include_router(monitoring_router)
app.include_router(feature_flags_router)
app.include_router(referrals_router)
app.include_router(notifications_router)

# Premium routes — active subscription required
app.include_router(meals_router, dependencies=_sub)
app.include_router(activities_router, dependencies=_sub)
app.include_router(meal_suggestions_router, dependencies=_sub)
app.include_router(user_profiles_router, dependencies=_sub)
app.include_router(foods_router, dependencies=_sub)
app.include_router(ingredients_router, dependencies=_sub)
app.include_router(tdee_router, dependencies=_sub)
app.include_router(saved_suggestions_router, dependencies=_sub)
app.include_router(cheat_days_router, dependencies=_sub)
app.include_router(nutrition_router, dependencies=_sub)
app.include_router(weight_entries_router, dependencies=_sub)
```

**Note:** `notifications_router` is kept public so users can register device push tokens before subscribing. `user_profiles_router` is gated. Review with the team if onboarding profile creation needs an exception.

- [ ] **Step 2: Run the unit test suite to verify no regressions**

```bash
python3.11 -m pytest tests/unit/ -q --tb=short --ignore=tests/unit/api/middleware/test_rate_limit.py --ignore=tests/unit/api/test_meal_suggestions_routes.py --ignore=tests/unit/domain/test_feature_flags.py --ignore=tests/unit/infra/adapters/test_deepl_translation_adapter.py 2>&1 | tail -10
```

Expected: Same pass count as baseline, no new failures.

- [ ] **Step 3: Commit**

```bash
git add src/api/main.py
git commit -m "feat(subscription): gate premium routers behind require_subscription"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ `SUBSCRIPTION_GRACE_PERIOD_HOURS` in Settings → Task 1
- ✅ DB-only `require_subscription`, no RC API calls → Task 2
- ✅ Grace period table (active/cancelled/billing_issue/refunded/expired) → Task 2 Step 3
- ✅ Router gating (all premium routers) → Task 3
- ✅ Public routes remain ungated → Task 3
- ✅ Unit tests covering all grace period scenarios → Task 2 Step 1
- ✅ `get_subscription_status` RC fallback removed → Task 2 Step 3

**Type consistency check:**
- `_has_subscription_access(subscriptions, grace_period_hours: int)` — same signature in tests (Task 2 Step 1) and implementation (Task 2 Step 3) ✅
- `require_subscription(request: Request)` — same signature throughout ✅
- `get_subscription_status(request: Request) -> dict` — same signature throughout ✅

**Duplicate `monitoring_router`:** Fixed inline — only appears once in the public section.
