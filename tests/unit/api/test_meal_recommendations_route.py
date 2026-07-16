import pytest
from fastapi import HTTPException
from starlette.requests import Request
from tests.unit.infra.repositories.test_meal_recommendation_plan_repository_async import (
    _plan,
)

from src.api.routes.v1.meal_recommendations import (
    _to_response,
    create_three_day_recommendations,
)
from src.app.commands.meal_recommendation import CreateThreeDayMealRecommendationCommand
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.app.queries.user import GetUserTimezoneQuery


class _EventBus:
    def __init__(self):
        self.commands = []

    async def send(self, message):
        self.commands.append(message)
        if isinstance(message, GetUserTimezoneQuery):
            return "Asia/Ho_Chi_Minh"
        if isinstance(message, GetWeeklyBudgetQuery):
            return {"adjusted_daily_calories": 2150}
        return _plan()


def _request(timezone: str = "Asia/Ho_Chi_Minh") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/meal-recommendations/three-day",
            "client": ("127.0.0.1", 12345),
            "headers": [(b"x-timezone", timezone.encode("utf-8"))],
        }
    )


def test_meal_recommendation_response_includes_allergy_not_evaluated_and_slots():
    response = _to_response(_plan())

    assert response.id == "plan-1"
    assert response.allergy_evaluated is False
    assert response.slots[0].recipe_version_id == "version-1"
    assert response.slots[0].alternatives[0].recipe_version_id == "version-2"


@pytest.mark.asyncio
async def test_create_three_day_recommendations_rejects_blank_idempotency_key():
    with pytest.raises(HTTPException) as exc_info:
        await create_three_day_recommendations(
            request=_request(), idempotency_key="   ", user_id="user-1"
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_three_day_recommendations_snapshots_target_and_timezone():
    event_bus = _EventBus()

    response = await create_three_day_recommendations(
        request=_request(),
        idempotency_key=" key-1 ",
        user_id="user-1",
        event_bus=event_bus,
    )

    command = next(
        item
        for item in event_bus.commands
        if isinstance(item, CreateThreeDayMealRecommendationCommand)
    )
    assert response.id == "plan-1"
    assert command.idempotency_key == "key-1"
    assert command.timezone == "Asia/Ho_Chi_Minh"
    assert command.daily_calories == 2150
