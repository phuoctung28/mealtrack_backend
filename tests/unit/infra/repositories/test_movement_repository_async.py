from datetime import datetime, timezone

import pytest

from src.domain.model.movement import MovementEntry
from src.infra.repositories.movement_repository_async import AsyncMovementRepository


class _FakeScalarResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar_value = scalar_value

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one(self):
        return self._scalar_value


class _FakeResult:
    rowcount = 1

    def __init__(self, rows=None, scalar_value=None):
        self._scalar_result = _FakeScalarResult(rows=rows, scalar_value=scalar_value)

    def scalars(self):
        return self._scalar_result

    def scalar_one(self):
        return self._scalar_result.scalar_one()


class _FakeSession:
    def __init__(self, result=None):
        self.result = result or _FakeResult()
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return self.result


def _compiled_sql(statement) -> str:
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def test_movement_entry_defaults_to_manual_source_and_include_in_balance():
    entry = MovementEntry(
        user_id="user-1",
        activity_name="Badminton",
        duration_min=60,
        kcal_burned=231.0,
        intensity="moderate",
        logged_at=datetime(2026, 5, 31, 5, 0, tzinfo=timezone.utc),
    )

    assert entry.id.startswith("mvmt_")
    assert entry.source == "manual"
    assert entry.include_in_balance is True


@pytest.mark.asyncio
async def test_find_by_user_and_logged_range_filters_and_orders_entries():
    session = _FakeSession()
    repository = AsyncMovementRepository(session)
    start = datetime(2026, 5, 31, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)

    entries = await repository.find_by_user_and_logged_range("user-1", start, end)

    assert entries == []
    sql = _compiled_sql(session.statements[0])
    assert "movement_entries.user_id = 'user-1'" in sql
    assert "movement_entries.logged_at >= '2026-05-31 00:00:00+00:00'" in sql
    assert "movement_entries.logged_at < '2026-06-01 00:00:00+00:00'" in sql
    assert (
        "ORDER BY movement_entries.logged_at DESC, movement_entries.created_at DESC"
        in sql
    )


@pytest.mark.asyncio
async def test_sum_included_kcal_for_range_filters_to_balance_entries():
    session = _FakeSession(result=_FakeResult(scalar_value=231.0))
    repository = AsyncMovementRepository(session)
    start = datetime(2026, 5, 31, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)

    total = await repository.sum_included_kcal_for_range("user-1", start, end)

    assert total == 231.0
    sql = _compiled_sql(session.statements[0])
    assert "coalesce(sum(movement_entries.kcal_burned), 0.0)" in sql
    assert "movement_entries.user_id = 'user-1'" in sql
    assert "movement_entries.include_in_balance IS true" in sql
    assert "movement_entries.logged_at >= '2026-05-31 00:00:00+00:00'" in sql
    assert "movement_entries.logged_at < '2026-06-01 00:00:00+00:00'" in sql


@pytest.mark.asyncio
async def test_find_by_id_scopes_by_user_and_entry_id():
    session = _FakeSession()
    repository = AsyncMovementRepository(session)

    entry = await repository.find_by_id("user-1", "mvmt_123")

    assert entry is None
    sql = _compiled_sql(session.statements[0])
    assert "movement_entries.id = 'mvmt_123'" in sql
    assert "movement_entries.user_id = 'user-1'" in sql


@pytest.mark.asyncio
async def test_delete_scopes_by_user_and_entry_id():
    session = _FakeSession()
    repository = AsyncMovementRepository(session)

    deleted = await repository.delete("user-1", "mvmt_123")

    assert deleted is True
    sql = _compiled_sql(session.statements[0])
    assert "DELETE FROM movement_entries" in sql
    assert "movement_entries.id = 'mvmt_123'" in sql
    assert "movement_entries.user_id = 'user-1'" in sql
