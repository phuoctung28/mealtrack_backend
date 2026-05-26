from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.app.commands.hydration import LogCaloricDrinkCommand
from src.app.handlers.command_handlers.log_caloric_drink_command_handler import (
    LogCaloricDrinkCommandHandler,
)


class _Users:
    async def find_by_id(self, user_id):
        return None


class _Meals:
    def __init__(self):
        self.saved = None

    async def save(self, meal):
        self.saved = meal
        return meal


class _Uow:
    def __init__(self):
        self.users = _Users()
        self.meals = _Meals()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_log_caloric_drink_response_exposes_calories_alias():
    event_bus = AsyncMock()
    handler = LogCaloricDrinkCommandHandler(uow=_Uow(), event_bus=event_bus)

    result = await handler.handle(
        LogCaloricDrinkCommand(
            user_id="22222222-2222-2222-2222-222222222222",
            drink_id="coke",
            volume_ml=330,
            target_date=date(2026, 5, 26),
        )
    )

    assert result["kcal"] == pytest.approx(140.0)
    assert result["calories"] == pytest.approx(140.0)


@pytest.mark.asyncio
async def test_log_caloric_drink_credits_hydration_weight_and_localizes_name():
    event_bus = AsyncMock()
    uow = _Uow()
    handler = LogCaloricDrinkCommandHandler(uow=uow, event_bus=event_bus)

    result = await handler.handle(
        LogCaloricDrinkCommand(
            user_id="22222222-2222-2222-2222-222222222222",
            drink_id="oj",
            volume_ml=350,
            target_date=date(2026, 5, 26),
            language="vi",
        )
    )

    assert uow.meals.saved.quantity == 333
    assert result["volume_ml"] == 333
    assert result["drink_name"] == "Nước ép"
