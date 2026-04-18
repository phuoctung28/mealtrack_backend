"""Tests for B8: translation pipelining in ParallelRecipeGenerator."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.services.meal_suggestion.parallel_recipe_generator import ParallelRecipeGenerator


def _make_suggestion(name: str) -> MealSuggestion:
    s = MagicMock(spec=MealSuggestion)
    s.meal_name = name
    return s


def _make_generator() -> tuple:
    from src.infra.services.ai.schemas import MealNamesResponse, DiscoveryMealsResponse
    translate_svc = MagicMock()
    translate_svc.translate_meal_suggestions_batch = AsyncMock(
        side_effect=lambda batch, lang: batch
    )
    gen = ParallelRecipeGenerator(
        generation_service=MagicMock(),
        translation_service=translate_svc,
        macro_validator=MagicMock(),
        nutrition_lookup=MagicMock(),
        meal_names_schema_class=MealNamesResponse,
        discovery_meals_schema_class=DiscoveryMealsResponse,
    )
    return gen, translate_svc


def _make_session(language: str = "en") -> SuggestionSession:
    s = MagicMock(spec=SuggestionSession)
    s.language = language
    s.id = "test-session"
    return s


@pytest.mark.asyncio
async def test_pipeline_translates_per_recipe_not_batch():
    """_phase2_and_translate calls translate_meal_suggestions_batch once per recipe."""
    gen, translate_svc = _make_generator()
    session = _make_session(language="vi")
    suggestions = [_make_suggestion(f"Meal {i}") for i in range(3)]

    async def fake_generate_with_retry(prompt, name, index, system, sess):
        return suggestions[index]

    meal_names = ["Meal 0", "Meal 1", "Meal 2"]

    with patch.object(gen, "_generate_with_retry", side_effect=fake_generate_with_retry):
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
