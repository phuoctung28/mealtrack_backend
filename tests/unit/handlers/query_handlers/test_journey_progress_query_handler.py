from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from src.app.handlers.query_handlers.get_journey_progress_query_handler import (
    GetJourneyProgressQueryHandler,
)
from src.app.queries.progress import GetJourneyProgressQuery


class _FakeUsers:
    async def find_by_id(self, user_id):
        return SimpleNamespace(timezone="Asia/Ho_Chi_Minh")

    async def get_profile(self, user_id):
        return SimpleNamespace(
            fitness_goal="cut",
            weight_kg=80.0,
            target_weight_kg=75.0,
            goal_start_weight_kg=None,
            goal_started_at=None,
            journey_progress_seed_percent=25.0,
            challenge_duration="30_days",
            daily_water_goal_ml=2000,
        )


class _FakeMeals:
    def __init__(self):
        self.args = None

    async def fetch_journey_progress_meals(self, user_id, start_utc, end_utc):
        self.args = (user_id, start_utc, end_utc)
        return [
            {
                "logged_at": start_utc,
                "label": "Launch meal",
                "calories": 400.0,
                "protein_g": 20.0,
            }
        ]


class _EmptyRepo:
    async def fetch_journey_progress_hydration(self, *args):
        return []

    async def fetch_journey_progress_movements(self, *args):
        return []

    async def find_by_recorded_range(self, *args):
        return []


class _FakeUow:
    def __init__(self):
        self.users = _FakeUsers()
        self.meals = _FakeMeals()
        self.hydration_entries = _EmptyRepo()
        self.movement_entries = _EmptyRepo()
        self.weight_entries = _EmptyRepo()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


@pytest.mark.asyncio
async def test_handler_uses_stable_existing_user_period_start():
    uow = _FakeUow()
    user_id = str(UUID("11111111-1111-1111-1111-111111111111"))
    now = datetime(2026, 6, 22, 12, tzinfo=UTC)
    handler = GetJourneyProgressQueryHandler(
        uow=uow,
        now_fn=lambda: now,
        target_loader=lambda _: _targets(),
    )

    result = await handler.handle(GetJourneyProgressQuery(user_id=user_id))

    assert result["period_start"] == "2026-06-20T17:00:00+00:00"
    assert result["timeline_days"] == 30
    assert result["journey_progress_seed_percent"] == 25.0
    assert result["progress_percent"] > result["current_period_progress_percent"]
    assert result["latest_action"]["label"] == "Launch meal"
    assert uow.meals.args == (
        user_id,
        datetime(2026, 6, 20, 17, tzinfo=UTC),
        now,
    )


async def _targets():
    return 400.0, 20.0
