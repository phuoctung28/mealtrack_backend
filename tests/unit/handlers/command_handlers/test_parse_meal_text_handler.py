import pytest

from src.api.schemas.request.meal_requests import CreateManualMealFromFoodsRequest
from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.app.handlers.command_handlers.parse_meal_text_handler import (
    ParseMealTextHandler,
)
from src.domain.services.nutrition_calculation_service import convert_quantity_to_grams
from src.infra.services.ai.ai_model_manager import ModelPurpose


class _FakeAIManager:
    def __init__(self):
        self.call_kwargs = None

    async def generate(self, **kwargs):
        self.call_kwargs = kwargs
        return {
            "items": [
                {
                    "name": "Pho bowl",
                    "quantity": 1,
                    "unit": "one very full noodle bowl",
                    "english_unit": "one very full noodle bowl",
                    "calories": 560,
                    "protein": 30,
                    "carbs": 80,
                    "fat": 12,
                }
            ]
        }


class _FakeFatSecretService:
    async def search_foods(self, *args, **kwargs):
        return []


@pytest.mark.asyncio
async def test_parse_text_unit_stays_compatible_with_prompt_manual_save():
    ai_manager = _FakeAIManager()
    handler = ParseMealTextHandler(ai_manager=ai_manager)
    handler._fat_secret_service = _FakeFatSecretService()

    response = await handler.handle(
        ParseMealTextCommand(text="1 bowl pho", user_id="user-1", language="en")
    )
    item = response.items[0]

    assert ai_manager.call_kwargs["purpose"] == ModelPurpose.PARSE_TEXT
    assert ai_manager.call_kwargs["thinking_budget"] == 0
    assert item.unit == "one very full noodle bowl"
    assert item.protein == 30
    assert item.carbs == 80
    assert item.fat == 12

    quantity_in_grams = convert_quantity_to_grams(item.quantity, item.unit, item.name)
    factor = 100.0 / quantity_in_grams
    payload = {
        "dish_name": "Pho bowl",
        "source": "prompt",
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "custom_nutrition": {
                    "protein_per_100g": item.protein * factor,
                    "carbs_per_100g": item.carbs * factor,
                    "fat_per_100g": item.fat * factor,
                },
            }
        ],
    }

    assert CreateManualMealFromFoodsRequest.model_validate(payload)
