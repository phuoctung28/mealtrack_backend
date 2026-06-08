"""Tests for B8: translation pipelining in ParallelRecipeGenerator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.services.meal_suggestion.macro_validation_service import (
    MacroValidationService,
)
from src.domain.services.meal_suggestion.parallel_recipe_generator import (
    ParallelRecipeGenerator,
)


def _make_suggestion(name: str) -> MealSuggestion:
    s = MagicMock(spec=MealSuggestion)
    s.meal_name = name
    return s


def _make_generator() -> tuple:
    from src.infra.services.ai.schemas import (
        DiscoveryMealsResponse,
        MealNamesResponse,
        RecipeDetailsResponse,
    )

    translate_svc = MagicMock()
    translate_svc.translate_meal_suggestions_batch = AsyncMock(
        side_effect=lambda batch, lang: batch
    )
    gen = ParallelRecipeGenerator(
        generation_service=MagicMock(),
        translation_service=translate_svc,
        macro_validator=MacroValidationService(),
        nutrition_lookup=MagicMock(),
        meal_names_schema_class=MealNamesResponse,
        discovery_meals_schema_class=DiscoveryMealsResponse,
        recipe_details_schema_class=RecipeDetailsResponse,
    )
    return gen, translate_svc


def _make_session(language: str = "en") -> SuggestionSession:
    s = MagicMock(spec=SuggestionSession)
    s.language = language
    s.id = "test-session"
    return s


def _make_real_session() -> SuggestionSession:
    return SuggestionSession(
        id="test-session",
        user_id="user-1",
        meal_type="lunch",
        meal_portion_type="main",
        target_calories=500,
        ingredients=["chicken", "rice"],
        language="en",
    )


@pytest.mark.asyncio
async def test_pipeline_translates_per_recipe_not_batch():
    """_phase2_and_translate calls translate_meal_suggestions_batch once per recipe."""
    gen, translate_svc = _make_generator()
    session = _make_session(language="vi")
    suggestions = [_make_suggestion(f"Meal {i}") for i in range(3)]

    async def fake_generate_with_retry(prompt, name, index, system, sess):
        return suggestions[index]

    meal_names = ["Meal 0", "Meal 1", "Meal 2"]

    with patch.object(
        gen, "_generate_with_retry", side_effect=fake_generate_with_retry
    ):
        with patch(
            "src.domain.services.meal_suggestion.suggestion_prompt_builder.build_recipe_details_prompt",
            side_effect=lambda name, sess: f"prompt:{name}",
        ):
            result = await gen._phase2_and_translate(
                session, meal_names, "Vietnamese", suggestion_count=3
            )

    # translate_meal_suggestions_batch called once per recipe (3 times), not once for all
    assert translate_svc.translate_meal_suggestions_batch.call_count == 3
    assert len(result) == 3


@pytest.mark.asyncio
async def test_translate_single_returns_original_on_failure():
    """_translate_single falls back to the original suggestion on translation error."""
    gen, translate_svc = _make_generator()
    suggestion = _make_suggestion("Grilled Chicken")
    translate_svc.translate_meal_suggestions_batch = AsyncMock(
        side_effect=RuntimeError("API error")
    )

    result = await gen._translate_single(suggestion, "vi")

    assert result is suggestion  # returned original, not crashed


def test_recipe_system_uses_central_constant():
    """Inline recipe_system strings must be gone; SystemPrompts.RECIPE_GENERATION must be used."""
    import inspect

    from src.domain.services.meal_suggestion import parallel_recipe_generator

    source = inspect.getsource(parallel_recipe_generator)
    # The inline string started with "You are a professional chef. Return ONLY this exact JSON structure"
    assert (
        "You are a professional chef. Return ONLY this exact JSON structure"
        not in source
    )


@pytest.mark.asyncio
async def test_generate_discovery_falls_back_when_ai_unavailable():
    gen, _ = _make_generator()
    session = _make_real_session()
    unavailable = AIUnavailableError(
        "All models failed for discovery",
        attempted_models=["gemini-2.5-flash-lite", "gemini-2.5-flash"],
        last_error="429 RESOURCE_EXHAUSTED",
    )
    gen._generation.generate_meal_plan.side_effect = unavailable

    meals = await gen.generate_discovery(session, exclude_meal_names=[], count=4)

    assert len(meals) == 4
    assert all(meal["id"].startswith("disc_") for meal in meals)
    assert all(meal["name"] == meal["english_name"] for meal in meals)
    assert all(meal["calories"] > 0 for meal in meals)
    call_args = gen._generation.generate_meal_plan.call_args.args
    assert call_args[-1] == "discovery"


@pytest.mark.asyncio
async def test_generate_discovery_tops_up_partial_ai_results():
    gen, _ = _make_generator()
    session = _make_real_session()
    gen._generation.generate_meal_plan.return_value = {
        "meals": [
            {
                "name": "Chicken Rice Bowl",
                "calories": 500,
                "protein": 35,
                "carbs": 50,
                "fat": 15,
            }
        ]
    }

    meals = await gen.generate_discovery(
        session,
        exclude_meal_names=["Chicken Rice Plate"],
        count=4,
    )

    assert len(meals) == 4
    assert meals[0]["name"] == "Chicken Rice Bowl"
    assert len({meal["name"] for meal in meals}) == 4
    assert "Chicken Rice Plate" not in {meal["name"] for meal in meals}
