"""
Unit tests verifying that _phase2_generate_recipes preserves submission order
when preserve_order=True (the default used by the /recipes endpoint).

Regression test for: asyncio.as_completed yielding results in completion-time
order, causing mobile index-based pairing to mismatch meal names with recipes.
"""

import asyncio
import uuid
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.model.meal_suggestion.meal_suggestion import (
    Ingredient,
    MacroEstimate,
    MealSuggestion,
    MealType,
    RecipeStep,
    SuggestionStatus,
)
from src.domain.model.meal_suggestion.suggestion_session import SuggestionSession
from src.domain.services.meal_suggestion.parallel_recipe_generator import (
    ParallelRecipeGenerator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_session() -> SuggestionSession:
    return SuggestionSession(
        id="test-session",
        user_id="user-1",
        meal_type="lunch",
        meal_portion_type="main",
        target_calories=600,
        ingredients=[],
        language="en",
    )


def make_meal_suggestion(meal_name: str, index: int) -> MealSuggestion:
    return MealSuggestion(
        id=str(uuid.uuid4()),
        session_id="test-session",
        user_id="user-1",
        meal_name=meal_name,
        description=f"Description for {meal_name}",
        meal_type=MealType.LUNCH,
        macros=MacroEstimate(calories=600, protein=40.0, carbs=60.0, fat=15.0),
        ingredients=[Ingredient(name="chicken", amount=200.0, unit="g")],
        recipe_steps=[RecipeStep(step=1, instruction="Cook it", duration_minutes=10)],
        prep_time_minutes=20,
        confidence_score=0.9,
    )


def make_generator() -> ParallelRecipeGenerator:
    """Build a ParallelRecipeGenerator with mock dependencies."""
    from src.infra.services.ai.schemas import MealNamesResponse, DiscoveryMealsResponse

    generation_service = MagicMock()
    translation_service = MagicMock()
    macro_validator = MagicMock()
    nutrition_lookup = MagicMock()
    return ParallelRecipeGenerator(
        generation_service=generation_service,
        translation_service=translation_service,
        macro_validator=macro_validator,
        nutrition_lookup=nutrition_lookup,
        meal_names_schema_class=MealNamesResponse,
        discovery_meals_schema_class=DiscoveryMealsResponse,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPhase2PreservesSubmissionOrder:
    """_phase2_generate_recipes with preserve_order=True must return results in
    submission order regardless of which task completes first."""

    @pytest.mark.asyncio
    async def test_order_preserved_when_index1_fastest(self):
        """
        Setup: index=1 (Caesar Salad) finishes first, index=0 (Chicken Curry) last,
               index=2 (Teriyaki Bowl) in the middle.
        Expect: returned list is [Chicken Curry, Caesar Salad, Teriyaki Bowl] — submission order.
        """
        meal_names = ["Chicken Curry", "Caesar Salad", "Teriyaki Bowl"]
        session = make_session()

        # Delays simulate: index=1 fastest, index=2 middle, index=0 slowest.
        delays = {0: 0.05, 1: 0.01, 2: 0.03}

        async def fake_generate_with_retry(
            prompt: str,
            meal_name: str,
            index: int,
            recipe_system: str,
            session: SuggestionSession,
        ) -> Optional[MealSuggestion]:
            await asyncio.sleep(delays[index])
            return make_meal_suggestion(meal_name, index)

        generator = make_generator()

        with patch.object(
            generator, "_generate_with_retry", side_effect=fake_generate_with_retry
        ):
            with patch(
                "src.domain.services.meal_suggestion.suggestion_prompt_builder"
                ".build_recipe_details_prompt",
                return_value="mock-prompt",
            ):
                results = await generator._phase2_generate_recipes(
                    session,
                    meal_names,
                    "English",
                    suggestion_count=3,
                    preserve_order=True,
                )

        assert len(results) == 3
        assert results[0].meal_name == "Chicken Curry"
        assert results[1].meal_name == "Caesar Salad"
        assert results[2].meal_name == "Teriyaki Bowl"

    @pytest.mark.asyncio
    async def test_order_matches_submitted_names_exactly(self):
        """Each result's meal_name must match the name at the same submission index."""
        meal_names = ["Pasta Bolognese", "Miso Soup", "Greek Salad"]
        session = make_session()

        # Reverse completion order: index=2 fastest, index=0 slowest.
        delays = {0: 0.06, 1: 0.03, 2: 0.01}

        async def fake_generate_with_retry(
            prompt: str,
            meal_name: str,
            index: int,
            recipe_system: str,
            session: SuggestionSession,
        ) -> Optional[MealSuggestion]:
            await asyncio.sleep(delays[index])
            return make_meal_suggestion(meal_name, index)

        generator = make_generator()

        with patch.object(
            generator, "_generate_with_retry", side_effect=fake_generate_with_retry
        ):
            with patch(
                "src.domain.services.meal_suggestion.suggestion_prompt_builder"
                ".build_recipe_details_prompt",
                return_value="mock-prompt",
            ):
                results = await generator._phase2_generate_recipes(
                    session,
                    meal_names,
                    "English",
                    suggestion_count=3,
                    preserve_order=True,
                )

        for i, (result, expected_name) in enumerate(zip(results, meal_names)):
            assert (
                result.meal_name == expected_name
            ), f"Index {i}: expected '{expected_name}', got '{result.meal_name}'"

    @pytest.mark.asyncio
    async def test_none_results_filtered_out_and_order_preserved(self):
        """When one task returns None (failure), remaining results keep submission order."""
        meal_names = ["Burger", "Salad", "Soup"]
        session = make_session()

        async def fake_generate_with_retry(
            prompt: str,
            meal_name: str,
            index: int,
            recipe_system: str,
            session: SuggestionSession,
        ) -> Optional[MealSuggestion]:
            if index == 1:
                return None  # Salad generation fails
            return make_meal_suggestion(meal_name, index)

        generator = make_generator()

        with patch.object(
            generator, "_generate_with_retry", side_effect=fake_generate_with_retry
        ):
            with patch(
                "src.domain.services.meal_suggestion.suggestion_prompt_builder"
                ".build_recipe_details_prompt",
                return_value="mock-prompt",
            ):
                results = await generator._phase2_generate_recipes(
                    session,
                    meal_names,
                    "English",
                    suggestion_count=3,
                    min_acceptable_override=1,
                    preserve_order=True,
                )

        assert len(results) == 2
        assert results[0].meal_name == "Burger"
        assert results[1].meal_name == "Soup"

    @pytest.mark.asyncio
    async def test_exception_in_task_logged_and_skipped(self):
        """Exceptions from tasks are logged as warnings, not raised; other results preserved."""
        meal_names = ["Steak", "Ramen", "Tacos"]
        session = make_session()

        async def fake_generate_with_retry(
            prompt: str,
            meal_name: str,
            index: int,
            recipe_system: str,
            session: SuggestionSession,
        ) -> Optional[MealSuggestion]:
            if index == 0:
                raise ValueError("AI service timeout")
            return make_meal_suggestion(meal_name, index)

        generator = make_generator()

        with patch.object(
            generator, "_generate_with_retry", side_effect=fake_generate_with_retry
        ):
            with patch(
                "src.domain.services.meal_suggestion.suggestion_prompt_builder"
                ".build_recipe_details_prompt",
                return_value="mock-prompt",
            ):
                results = await generator._phase2_generate_recipes(
                    session,
                    meal_names,
                    "English",
                    suggestion_count=3,
                    min_acceptable_override=1,
                    preserve_order=True,
                )

        # Steak (index=0) failed; Ramen and Tacos succeed in submission order.
        assert len(results) == 2
        assert results[0].meal_name == "Ramen"
        assert results[1].meal_name == "Tacos"

    @pytest.mark.asyncio
    async def test_preserve_order_false_does_not_guarantee_order(self):
        """preserve_order=False (discovery flow) uses as_completed — order is non-deterministic.
        This test just verifies the path executes without error and returns correct count.
        """
        meal_names = ["Meal A", "Meal B", "Meal C", "Meal D"]
        session = make_session()

        async def fake_generate_with_retry(
            prompt: str,
            meal_name: str,
            index: int,
            recipe_system: str,
            session: SuggestionSession,
        ) -> Optional[MealSuggestion]:
            return make_meal_suggestion(meal_name, index)

        generator = make_generator()

        with patch.object(
            generator, "_generate_with_retry", side_effect=fake_generate_with_retry
        ):
            with patch(
                "src.domain.services.meal_suggestion.suggestion_prompt_builder"
                ".build_recipe_details_prompt",
                return_value="mock-prompt",
            ):
                results = await generator._phase2_generate_recipes(
                    session,
                    meal_names,
                    "English",
                    suggestion_count=3,
                    preserve_order=False,
                )

        # Should stop after 3 successes (early-stop).
        assert len(results) == 3
        # All results should be valid MealSuggestion objects.
        for r in results:
            assert isinstance(r, MealSuggestion)
            assert r.meal_name in meal_names
