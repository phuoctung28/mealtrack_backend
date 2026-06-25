import pytest

from src.api.schemas.request.meal_requests import CreateManualMealFromFoodsRequest
from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.app.handlers.command_handlers.parse_meal_text_handler import (
    ParseMealTextHandler,
)
from src.domain.exceptions.ai_exceptions import (
    AIOutputValidationError,
    AIUnavailableError,
)
from src.domain.model.ai.nutrition_contracts import MealTextNutritionResponse
from src.domain.services.nutrition_calculation_service import convert_quantity_to_grams


class _FakeMealGenerationService:
    def __init__(self, responses=None):
        self.call_kwargs = None
        self.calls = []
        self._responses = list(responses) if responses is not None else None

    async def generate_meal_plan_async(self, **kwargs):
        self.call_kwargs = kwargs
        self.calls.append(kwargs)
        if self._responses is not None:
            response = self._responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        return _valid_parse_text_response()


def _valid_parse_text_response():
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


class _HighCalorieFatSecretService:
    async def search_foods(self, *args, **kwargs):
        return [{"food_name": "Pho concentrate"}]


@pytest.mark.asyncio
async def test_parse_text_unit_stays_compatible_with_prompt_manual_save():
    meal_generation_service = _FakeMealGenerationService()
    handler = ParseMealTextHandler(
        meal_generation_service=meal_generation_service,
        fat_secret_service=_FakeFatSecretService(),
    )

    response = await handler.handle(
        ParseMealTextCommand(text="1 bowl pho", user_id="user-1", language="en")
    )
    item = response.items[0]

    assert meal_generation_service.call_kwargs["model_purpose"] == "parse_text"
    assert meal_generation_service.call_kwargs["thinking_budget"] == 0
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


@pytest.mark.asyncio
async def test_parse_text_retries_invalid_ai_output_once():
    meal_generation_service = _FakeMealGenerationService(
        responses=[
            {
                "items": [
                    {
                        "name": "Pho bowl",
                        "quantity": 150000,
                        "unit": "bowl",
                        "protein": 30,
                        "carbs": 80,
                        "fat": 12,
                    }
                ]
            },
            _valid_parse_text_response(),
        ]
    )
    handler = ParseMealTextHandler(
        meal_generation_service=meal_generation_service,
        fat_secret_service=_FakeFatSecretService(),
    )

    response = await handler.handle(
        ParseMealTextCommand(text="1 bowl pho", user_id="user-1", language="en")
    )

    assert len(meal_generation_service.calls) == 2
    assert (
        "Return the full corrected response"
        in meal_generation_service.calls[1]["system_message"]
    )
    assert "items.0.quantity" in meal_generation_service.calls[1]["system_message"]
    assert response.items[0].name == "Pho bowl"
    assert response.items[0].protein == 30
    assert response.total_carbs == 80


@pytest.mark.asyncio
async def test_parse_text_raises_controlled_error_after_retry_failure():
    invalid = {
        "items": [
            {
                "name": "Pho bowl",
                "quantity": 150000,
                "unit": "bowl",
                "protein": 30,
                "carbs": 80,
                "fat": 12,
            }
        ]
    }
    meal_generation_service = _FakeMealGenerationService(responses=[invalid, invalid])
    handler = ParseMealTextHandler(
        meal_generation_service=meal_generation_service,
        fat_secret_service=_FakeFatSecretService(),
    )

    with pytest.raises(AIOutputValidationError) as exc_info:
        await handler.handle(
            ParseMealTextCommand(text="1 bowl pho", user_id="user-1", language="en")
        )

    assert len(meal_generation_service.calls) == 2
    assert exc_info.value.purpose == "parse_text"
    assert exc_info.value.attempt_count == 2
    assert "items.0.quantity" in exc_info.value.validation_details[0]


@pytest.mark.asyncio
async def test_parse_text_does_not_retry_provider_outage():
    unavailable = AIUnavailableError(
        "All parse text models failed",
        attempted_models=["gpt-5.4-mini-2026-03-17", "gpt-5.4-mini-2026-03-17"],
        last_error="503 UNAVAILABLE",
    )
    meal_generation_service = _FakeMealGenerationService(responses=[unavailable])
    handler = ParseMealTextHandler(
        meal_generation_service=meal_generation_service,
        fat_secret_service=_FakeFatSecretService(),
    )

    with pytest.raises(AIUnavailableError):
        await handler.handle(
            ParseMealTextCommand(text="1 bowl pho", user_id="user-1", language="en")
        )

    assert len(meal_generation_service.calls) == 1


@pytest.mark.asyncio
async def test_parse_text_rejects_fatsecret_using_backend_derived_calories(
    monkeypatch,
):
    meal_generation_service = _FakeMealGenerationService(
        responses=[
            {
                "items": [
                    {
                        "name": "Pho bowl",
                        "quantity": 1,
                        "unit": "bowl",
                        "english_unit": "bowl",
                        "protein": 10,
                        "carbs": 10,
                        "fat": 0,
                    }
                ]
            }
        ]
    )
    monkeypatch.setattr(
        "src.app.handlers.command_handlers.parse_meal_text_handler."
        "parse_fatsecret_nutrition",
        lambda _food: {"calories": 1000, "protein": 0, "carbs": 0, "fat": 100},
    )
    monkeypatch.setattr(
        "src.app.handlers.command_handlers.parse_meal_text_handler."
        "scale_per_100g_nutrition",
        lambda *args, **kwargs: {
            "calories": 1000,
            "protein": 0,
            "carbs": 0,
            "fat": 100,
        },
    )
    handler = ParseMealTextHandler(
        meal_generation_service=meal_generation_service,
        fat_secret_service=_HighCalorieFatSecretService(),
    )

    response = await handler.handle(
        ParseMealTextCommand(text="1 bowl pho", user_id="user-1", language="en")
    )
    item = response.items[0]

    assert item.data_source == "ai_estimate"
    assert item.protein == 10
    assert item.carbs == 10
    assert item.fat == 0
