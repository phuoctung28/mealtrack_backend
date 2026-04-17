"""Tests that parallel_recipe_generator emits phase spans during generation."""
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.domain.services.meal_suggestion.parallel_recipe_generator import ParallelRecipeGenerator
from src.domain.model.meal_suggestion import SuggestionSession


def _make_generator():
    mock_generation = MagicMock()
    mock_translation = MagicMock()
    mock_validator = MagicMock()
    mock_nutrition = MagicMock()
    return ParallelRecipeGenerator(
        generation_service=mock_generation,
        translation_service=mock_translation,
        macro_validator=mock_validator,
        nutrition_lookup=mock_nutrition,
    )


def _make_session(language="en"):
    session = MagicMock(spec=SuggestionSession)
    session.id = "sess-1"
    session.language = language
    session.meal_type = "lunch"
    session.target_calories = 500
    return session


def _mock_span():
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=False)
    return span


@pytest.mark.asyncio
async def test_generate_emits_phase1_and_phase2_spans():
    """generate() emits Phase 1 and Phase 2 spans."""
    gen = _make_generator()
    session = _make_session(language="en")

    mock_span = _mock_span()
    span_calls = []

    def track_span(op=None, name=None, **kwargs):
        span_calls.append((op, name))
        return mock_span

    mock_meals = [MagicMock(), MagicMock(), MagicMock()]

    with patch("sentry_sdk.start_span", side_effect=track_span):
        with patch.object(gen, "_phase1_generate_names", new_callable=AsyncMock, return_value=["Salad", "Pasta", "Rice", "Soup"]):
            with patch.object(gen, "_phase2_generate_recipes", new_callable=AsyncMock, return_value=mock_meals):
                result = await gen.generate(session=session, exclude_meal_names=[])

    assert ("gen_ai.invoke_agent", "Phase 1: Generate meal names") in span_calls
    assert ("gen_ai.invoke_agent", "Phase 2: Generate recipes") in span_calls


@pytest.mark.asyncio
async def test_generate_emits_phase3_span_for_non_english():
    """generate() emits Phase 3 span when language is not English."""
    gen = _make_generator()
    session = _make_session(language="vi")

    mock_span = _mock_span()
    span_calls = []

    def track_span(op=None, name=None, **kwargs):
        span_calls.append((op, name))
        return mock_span

    mock_meals = [MagicMock(), MagicMock(), MagicMock()]
    translated_meals = [MagicMock(), MagicMock(), MagicMock()]

    with patch("sentry_sdk.start_span", side_effect=track_span):
        with patch.object(gen, "_phase1_generate_names", new_callable=AsyncMock, return_value=["Phở", "Bún", "Cơm", "Bánh"]):
            with patch.object(gen, "_phase2_generate_recipes", new_callable=AsyncMock, return_value=mock_meals):
                with patch.object(gen, "_phase3_translate", new_callable=AsyncMock, return_value=(translated_meals, 1.5)):
                    result = await gen.generate(session=session, exclude_meal_names=[])

    assert ("gen_ai.invoke_agent", "Phase 3: Translate") in span_calls
