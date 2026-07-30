from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from starlette.requests import Request

from src.api.routes.v1 import meal_scan_by_url


class FakeEventBus:
    def __init__(self, meal):
        self.meal = meal

    async def send(self, command):
        self.command = command
        return self.meal


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/meals/scan-by-url",
            "headers": [(b"accept-language", b"en")],
            "state": {"language": "en"},
        }
    )


@pytest.mark.asyncio
async def test_scan_by_url_schedules_profile_aware_value_insights(monkeypatch):
    meal = SimpleNamespace(
        meal_id="meal-1",
        status=SimpleNamespace(value="READY"),
        image=SimpleNamespace(url="https://res.cloudinary.com/demo/mealtrack/img.jpg"),
    )
    scheduler = Mock()
    monkeypatch.setattr(
        meal_scan_by_url,
        "schedule_value_insight_generation",
        scheduler,
    )
    monkeypatch.setattr(
        meal_scan_by_url.MealMapper,
        "to_detailed_response",
        lambda *args, **kwargs: {"ok": True},
    )
    cache_service = object()
    task_manager = object()
    ai_manager = object()
    event_bus = FakeEventBus(meal)

    result = await meal_scan_by_url._scan_by_url(
        request=_request(),
        user_id="user-1",
        event_bus=event_bus,
        image_url="https://res.cloudinary.com/demo/mealtrack/img.jpg",
        image_id="img",
        target_date=None,
        user_description=None,
        scan_mode="scanner",
        cache_service=cache_service,
        task_manager=task_manager,
        ai_manager=ai_manager,
    )

    assert result == {"ok": True}
    scheduler.assert_called_once_with(
        task_manager,
        meal,
        language="en",
        cache_service=cache_service,
        ai_manager=ai_manager,
        event_bus=event_bus,
        user_id="user-1",
        source="api",
    )
