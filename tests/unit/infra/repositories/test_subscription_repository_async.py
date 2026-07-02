from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.infra.repositories.subscription_repository_async import (
    AsyncSubscriptionRepository,
)


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _Scalars(self._rows)


class _AsyncSession:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _Result(self.rows)


def test_async_subscription_repository_satisfies_port_contract():
    assert AsyncSubscriptionRepository.__abstractmethods__ == frozenset()


@pytest.mark.asyncio
async def test_find_expiring_in_window_uses_active_expiry_bounds():
    rows = [MagicMock(id="sub-1")]
    session = _AsyncSession(rows)
    repo = AsyncSubscriptionRepository(session)
    now = datetime(2026, 6, 9, tzinfo=UTC)

    result = await repo.find_expiring_in_window(from_days=1, to_days=2, now=now)

    assert result == rows
    compiled = str(session.statement)
    assert "subscriptions.status" in compiled
    assert "subscriptions.expires_at >= " in compiled
    assert "subscriptions.expires_at < " in compiled


@pytest.mark.asyncio
async def test_find_expiring_soon_returns_active_future_rows():
    rows = [MagicMock(id="sub-2")]
    session = _AsyncSession(rows)
    repo = AsyncSubscriptionRepository(session)

    result = await repo.find_expiring_soon(days_until_expiry=7)

    assert result == rows
    compiled = str(session.statement)
    assert "subscriptions.status" in compiled
    assert "subscriptions.expires_at <= " in compiled
    assert "subscriptions.expires_at > " in compiled


@pytest.mark.asyncio
async def test_find_trial_end_offer_candidates_allows_cancelled_unexpired_trials():
    rows = [MagicMock(id="sub-trial")]
    session = _AsyncSession(rows)
    repo = AsyncSubscriptionRepository(session)
    now = datetime(2026, 6, 9, tzinfo=UTC)

    result = await repo.find_trial_end_offer_candidates(lookahead_days=1, now=now)

    assert result == rows
    compiled = str(session.statement)
    assert "subscriptions.status IN" in compiled
    assert "subscriptions.expires_at > " in compiled
    assert "subscriptions.expires_at < " in compiled
    assert "trial_end_discount_claimed_at IS NULL" in compiled
    assert "lower(subscriptions.period_type)" in compiled
