from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.commands.meal.upload_meal_image_immediately_command import (
    UploadMealImageImmediatelyCommand,
)
from src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler import (
    UploadMealImageImmediatelyHandler,
)
from src.domain.services.meal_analysis.fast_path_policy import MealAnalyzeFastPathPolicy


@pytest.mark.asyncio
async def test_translation_not_called_when_policy_disables_critical_path():
    saved_state = {}
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users = MagicMock()
    mock_uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    mock_uow.meals = MagicMock()

    async def save_meal(meal):
        saved_state["meal"] = meal
        return meal

    async def find_meal(meal_id, projection=None):
        return saved_state["meal"]

    mock_uow.meals.save = AsyncMock(side_effect=save_meal)
    mock_uow.meals.find_by_id = AsyncMock(side_effect=find_meal)
    mock_uow.commit = AsyncMock()

    mock_event_bus = MagicMock()
    mock_event_bus.publish = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=mock_uow,
        event_bus=mock_event_bus,
        fast_path_policy=MealAnalyzeFastPathPolicy(translation_in_critical_path=False),
    )
    handler.image_store = MagicMock()
    handler.image_store.save.return_value = (
        "mock://images/00000000-0000-0000-0000-000000000123"
    )
    handler.vision_service = MagicMock()
    handler.vision_service.analyze.return_value = {"dish_name": "Pho"}
    handler.gpt_parser = MagicMock()
    handler.gpt_parser.parse_to_nutrition.return_value = SimpleNamespace(
        food_items=[MagicMock()], calories=400
    )
    handler.gpt_parser.parse_dish_name.return_value = "Pho"
    handler.gpt_parser.parse_emoji.return_value = "🍲"
    handler.gpt_parser.extract_raw_json.return_value = "{}"
    handler.meal_translation_service = MagicMock()
    handler.meal_translation_service.translate_meal = AsyncMock()

    command = UploadMealImageImmediatelyCommand(
        user_id="00000000-0000-0000-0000-000000000001",
        file_contents=b"img",
        content_type="image/jpeg",
        language="vi",
    )

    await handler.handle(command)

    handler.meal_translation_service.translate_meal.assert_not_called()
