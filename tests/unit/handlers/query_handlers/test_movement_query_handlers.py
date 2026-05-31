from datetime import date, datetime, timezone

import pytest

from src.app.handlers.query_handlers.get_daily_movement_query_handler import (
    GetDailyMovementQueryHandler,
)
from src.app.handlers.query_handlers.get_movement_catalog_query_handler import (
    GetMovementCatalogQueryHandler,
)
from src.app.queries.movement import GetDailyMovementQuery, GetMovementCatalogQuery
from src.domain.model.movement import MovementEntry


@pytest.mark.asyncio
async def test_get_movement_catalog_query_returns_activities():
    handler = GetMovementCatalogQueryHandler()

    result = await handler.handle(GetMovementCatalogQuery())

    assert "activities" in result
    assert any(item["id"] == "badminton" for item in result["activities"])


class _FakeUsers:
    async def find_by_id(self, user_id):
        return None


class _FakeMovementEntries:
    def __init__(self, entries):
        self.entries = entries
        self.range_args = None

    async def find_by_user_and_logged_range(self, user_id, start_utc, end_utc):
        self.range_args = (user_id, start_utc, end_utc)
        return self.entries


class _FakeUow:
    def __init__(self, entries):
        self.users = _FakeUsers()
        self.movement_entries = _FakeMovementEntries(entries)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


@pytest.mark.asyncio
async def test_daily_movement_query_serializes_entries_for_local_day():
    entry = MovementEntry(
        id="entry-1",
        user_id="user-1",
        activity_id="badminton",
        activity_name="Badminton",
        duration_min=60,
        kcal_burned=231.0,
        intensity="moderate",
        include_in_balance=True,
        source="manual",
        logged_at=datetime(2026, 5, 29, 5, 0, tzinfo=timezone.utc),
    )
    uow = _FakeUow([entry])
    handler = GetDailyMovementQueryHandler(uow=uow)

    result = await handler.handle(
        GetDailyMovementQuery(
            user_id="user-1",
            target_date=date(2026, 5, 29),
            header_timezone="Asia/Ho_Chi_Minh",
        )
    )

    assert result == {
        "date": "2026-05-29",
        "goal_kcal": 300.0,
        "entries": [
            {
                "id": "entry-1",
                "activity_id": "badminton",
                "activity_name": "Badminton",
                "duration_min": 60,
                "kcal_burned": 231.0,
                "intensity": "moderate",
                "source": "manual",
                "include_in_balance": True,
                "logged_at": "2026-05-29T05:00:00+00:00",
            }
        ],
    }
    assert uow.movement_entries.range_args == (
        "user-1",
        datetime(2026, 5, 28, 17, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 29, 17, 0, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_day_boundary_parity_same_utc_window():
    """
    Both /movement/daily and /activities/daily must compute identical UTC windows
    for a given local date.

    HCM (UTC+7) day window for 2026-05-29:
      start = 2026-05-28 17:00 UTC
      end   = 2026-05-29 17:00 UTC

    An entry at 23:30 HCM (=16:30 UTC) must fall inside this window.
    An entry at 00:30 HCM next day (=17:30 UTC) must fall OUTSIDE this window.
    """
    inside_utc = datetime(2026, 5, 29, 16, 30, tzinfo=timezone.utc)   # 23:30 HCM May 29
    outside_utc = datetime(2026, 5, 29, 17, 30, tzinfo=timezone.utc)  # 00:30 HCM May 30

    uow = _FakeUow([])
    handler = GetDailyMovementQueryHandler(uow=uow)
    await handler.handle(
        GetDailyMovementQuery(
            user_id="user-1",
            target_date=date(2026, 5, 29),
            header_timezone="Asia/Ho_Chi_Minh",
        )
    )

    _, start_utc, end_utc = uow.movement_entries.range_args

    # Window must be [2026-05-28 17:00 UTC, 2026-05-29 17:00 UTC)
    assert start_utc == datetime(2026, 5, 28, 17, 0, tzinfo=timezone.utc)
    assert end_utc == datetime(2026, 5, 29, 17, 0, tzinfo=timezone.utc)

    # Boundary correctness
    assert start_utc <= inside_utc < end_utc, "23:30 HCM must be inside May 29 window"
    assert not (start_utc <= outside_utc < end_utc), "00:30 HCM next day must be outside May 29 window"
