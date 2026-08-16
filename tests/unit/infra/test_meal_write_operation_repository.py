from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.domain.utils.timezone_utils import utc_now
from src.infra.repositories.meal_write_operation_repository_async import (
    AsyncMealWriteOperationRepository,
)


def _result(row):
    scalars = SimpleNamespace(
        first=lambda: row, all=lambda: [] if row is None else [row]
    )
    return SimpleNamespace(scalars=lambda: scalars)


def _insert_result(operation_id=None):
    return SimpleNamespace(scalar_one_or_none=lambda: operation_id)


@pytest.mark.asyncio
async def test_new_reservation_is_acquired_by_the_inserting_caller():
    session = SimpleNamespace(execute=AsyncMock(return_value=_insert_result("op-new")))
    repo = AsyncMealWriteOperationRepository(session)

    reservation = await repo.reserve(
        user_id="user-1",
        operation="create_manual_meal",
        idempotency_key="brand-new-key",
        request_fingerprint="fingerprint-a",
    )

    assert reservation.state == "acquired"
    assert reservation.operation_id == "op-new"
    assert reservation.lease_owner is not None
    assert reservation.lease_generation == 1
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_reservation_replays_completed_operation_and_rejects_fingerprint_reuse():
    row = SimpleNamespace(
        id="op-1",
        request_fingerprint="fingerprint-a",
        status="completed",
        lease_owner=None,
        lease_generation=2,
        lease_expires_at=None,
        target_meal_id="meal-1",
        response={"meal_id": "meal-1"},
    )
    session = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _insert_result(),
                _result(row),
                _insert_result(),
                _result(row),
            ]
        )
    )
    repo = AsyncMealWriteOperationRepository(session)

    replay = await repo.reserve(
        user_id="user-1",
        operation="create_manual_meal",
        idempotency_key="key-1",
        request_fingerprint="fingerprint-a",
    )
    conflict = await repo.reserve(
        user_id="user-1",
        operation="create_manual_meal",
        idempotency_key="key-1",
        request_fingerprint="fingerprint-b",
    )

    assert replay.state == "replay"
    assert replay.target_meal_id == "meal-1"
    assert conflict.state == "fingerprint_conflict"


@pytest.mark.asyncio
async def test_active_existing_reservation_remains_in_progress_for_other_callers():
    row = SimpleNamespace(
        id="op-1",
        request_fingerprint="fingerprint-a",
        status="in_progress",
        lease_owner="current-owner",
        lease_generation=1,
        lease_expires_at=utc_now() + timedelta(seconds=30),
        target_meal_id=None,
        response=None,
    )
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[_insert_result(), _result(row)])
    )
    repo = AsyncMealWriteOperationRepository(session)

    reservation = await repo.reserve(
        user_id="user-1",
        operation="create_manual_meal",
        idempotency_key="key-1",
        request_fingerprint="fingerprint-a",
    )

    assert reservation.state == "in_progress"
    assert reservation.lease_owner == "current-owner"


@pytest.mark.asyncio
async def test_expired_lease_is_fenced_and_reacquired():
    row = SimpleNamespace(
        id="op-1",
        request_fingerprint="fingerprint-a",
        status="in_progress",
        lease_owner="old-owner",
        lease_generation=4,
        lease_expires_at=utc_now() - timedelta(seconds=1),
        target_meal_id=None,
        response=None,
    )
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[_insert_result(), _result(row)]),
        flush=AsyncMock(),
    )
    repo = AsyncMealWriteOperationRepository(session)

    reservation = await repo.reserve(
        user_id="user-1",
        operation="edit_meal",
        idempotency_key="key-1",
        request_fingerprint="fingerprint-a",
    )

    assert reservation.state == "acquired"
    assert reservation.lease_generation == 5
    assert row.lease_owner != "old-owner"


@pytest.mark.asyncio
async def test_cleanup_finished_is_bounded_and_does_not_touch_active_rows():
    session = SimpleNamespace(execute=AsyncMock(return_value=_result("op-old")))
    repo = AsyncMealWriteOperationRepository(session)

    deleted = await repo.cleanup_finished(
        older_than=utc_now() - timedelta(days=30),
        limit=100,
    )

    assert deleted == 1
    assert session.execute.await_count == 2
