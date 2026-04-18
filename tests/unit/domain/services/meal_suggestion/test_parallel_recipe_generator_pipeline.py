"""Tests for B8: translation pipelining in ParallelRecipeGenerator."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.services.meal_suggestion.parallel_recipe_generator import ParallelRecipeGenerator


def _make_generator() -> tuple[ParallelRecipeGenerator, MagicMock]:
    translate_svc = MagicMock()
    gen = ParallelRecipeGenerator(
        generation_service=MagicMock(),
        translation_service=translate_svc,
        macro_validator=MagicMock(),
        nutrition_lookup=MagicMock(),
    )
    return gen, translate_svc


def _make_suggestion(name: str) -> MealSuggestion:
    s = MagicMock(spec=MealSuggestion)
    s.meal_name = name
    return s


@pytest.mark.asyncio
async def test_non_english_translates_per_recipe_not_batch():
    """_translate_single is called once per recipe, not once for the whole batch."""
    gen, translate_svc = _make_generator()
    suggestions = [_make_suggestion(f"Meal {i}") for i in range(3)]
    # translate_meal_suggestions_batch([single], lang) → returns [single]
    translate_svc.translate_meal_suggestions_batch = AsyncMock(
        side_effect=lambda batch, lang: batch
    )

    results = await asyncio.gather(*[
        gen._translate_single(s, "vi") for s in suggestions
    ])

    assert translate_svc.translate_meal_suggestions_batch.call_count == 3
    assert len(results) == 3


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
