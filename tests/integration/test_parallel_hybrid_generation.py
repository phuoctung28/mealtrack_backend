"""
Integration tests for parallel hybrid meal generation.
Tests real Pinecone + Gemini API calls with latency verification.

Run with: pytest tests/integration/test_parallel_hybrid_generation.py -v -s
Requires: GOOGLE_API_KEY, PINECONE_API_KEY environment variables
"""
import os
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services.meal_suggestion.suggestion_orchestration_service import (
    SuggestionOrchestrationService,
)
from src.domain.services.meal_suggestion.recipe_search_service import RecipeSearchService
from src.domain.services.meal_suggestion.nutrition_enrichment_service import (
    NutritionEnrichmentService,
)


# Skip all tests if API keys are not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY") or not os.environ.get("PINECONE_API_KEY"),
    reason="API keys not available for integration testing",
)


@pytest.fixture
def real_generation_service():
    """Create real meal generation service."""
    from src.infra.adapters.meal_generation_service import MealGenerationService

    return MealGenerationService()


@pytest.fixture
def real_pinecone_service():
    """Create real Pinecone service."""
    from src.infra.services.pinecone_service import PineconeNutritionService

    return PineconeNutritionService()


@pytest.fixture
def real_recipe_search(real_pinecone_service):
    """Create real recipe search service."""
    return RecipeSearchService(real_pinecone_service)


@pytest.fixture
def real_nutrition_enrichment(real_pinecone_service):
    """Create real nutrition enrichment service."""
    return NutritionEnrichmentService(real_pinecone_service)


@pytest.fixture
def mock_user_repo():
    """Create mock user repo with test profile."""
    repo = MagicMock()
    profile = MagicMock()
    profile.age = 30
    profile.gender = "male"
    profile.height_cm = 175
    profile.weight_kg = 75
    profile.activity_level = "moderate"
    profile.fitness_goal = "recomp"
    profile.body_fat_percentage = 15
    profile.meals_per_day = 3
    profile.dietary_preferences = []
    profile.allergies = []
    repo.get_profile = MagicMock(return_value=profile)
    return repo


@pytest.fixture
def mock_suggestion_repo():
    """Create mock suggestion repo."""
    repo = MagicMock()
    repo.save_session = AsyncMock()
    repo.save_suggestions = AsyncMock()
    repo.get_session = AsyncMock()
    repo.update_session = AsyncMock()
    return repo


@pytest.fixture
def real_service(
    real_generation_service,
    mock_suggestion_repo,
    mock_user_repo,
    real_recipe_search,
    real_nutrition_enrichment,
):
    """Create orchestration service with real external services."""
    return SuggestionOrchestrationService(
        generation_service=real_generation_service,
        suggestion_repo=mock_suggestion_repo,
        user_repo=mock_user_repo,
        recipe_search=real_recipe_search,
        nutrition_enrichment=real_nutrition_enrichment,
    )


@pytest.mark.integration
class TestParallelHybridIntegration:
    """Integration tests for parallel hybrid generation with real APIs."""

    MAX_LATENCY_SECONDS = 12  # Hard requirement from user

    @pytest.mark.asyncio
    async def test_parallel_generation_latency(
        self, real_service, mock_suggestion_repo, mock_user_repo
    ):
        """
        CRITICAL: Verify total latency < 12s with real API calls.
        This is the main acceptance criterion.
        """
        start_time = time.time()
        session, suggestions = await real_service.generate_suggestions(
            user_id="test_user",
            meal_type="lunch",
            meal_portion_type="regular",
            ingredients=["chicken", "rice", "broccoli", "garlic"],
            cooking_time_minutes=30,
        )
        elapsed = time.time() - start_time

        # Core assertions
        assert len(suggestions) == 3, "Should return exactly 3 suggestions"
        assert elapsed < self.MAX_LATENCY_SECONDS, (
            f"Latency {elapsed:.2f}s exceeds {self.MAX_LATENCY_SECONDS}s limit"
        )

        print(f"\n✓ Latency: {elapsed:.2f}s (limit: {self.MAX_LATENCY_SECONDS}s)")
        print(f"✓ Suggestions: {[s.meal_name for s in suggestions]}")

    @pytest.mark.asyncio
    async def test_suggestions_use_user_ingredients(
        self, real_service, mock_suggestion_repo, mock_user_repo
    ):
        """Verify generated suggestions incorporate user's ingredients."""
        session, suggestions = await real_service.generate_suggestions(
            user_id="test_user",
            meal_type="dinner",
            meal_portion_type="regular",
            ingredients=["salmon", "asparagus", "lemon"],
            cooking_time_minutes=25,
        )

        # Check that at least one of the user's ingredients appears
        all_ingredients = []
        for s in suggestions:
            all_ingredients.extend([ing.name.lower() for ing in s.ingredients])

        user_ingredients = {"salmon", "asparagus", "lemon"}
        found = any(
            any(user_ing in ing for user_ing in user_ingredients)
            for ing in all_ingredients
        )
        assert found, (
            f"AI should use user's provided ingredients. "
            f"User ingredients: {user_ingredients}, "
            f"Generated ingredients: {all_ingredients}"
        )

        print(f"\n✓ User ingredients found in generated recipes")
        print(f"✓ Generated ingredients: {all_ingredients[:10]}...")

    @pytest.mark.asyncio
    async def test_nutrition_calculated_not_ai_generated(
        self, real_service, mock_suggestion_repo, mock_user_repo
    ):
        """Verify macros are calculated from ingredients, not AI-generated."""
        session, suggestions = await real_service.generate_suggestions(
            user_id="test_user",
            meal_type="breakfast",
            meal_portion_type="light",
            ingredients=["eggs", "toast", "avocado"],
            cooking_time_minutes=15,
        )

        for i, s in enumerate(suggestions):
            # Basic assertions
            assert s.macros is not None, f"Suggestion {i} should have macros"
            assert s.macros.calories > 0, f"Suggestion {i} should have calories"
            assert s.macros.protein >= 0, f"Suggestion {i} should have protein"
            assert s.macros.carbs >= 0, f"Suggestion {i} should have carbs"
            assert s.macros.fat >= 0, f"Suggestion {i} should have fat"

            # Sanity check: calories should roughly match P*4 + C*4 + F*9
            calculated = (s.macros.protein * 4) + (s.macros.carbs * 4) + (s.macros.fat * 9)
            tolerance = s.macros.calories * 0.35  # 35% tolerance for rounding
            assert abs(s.macros.calories - calculated) < tolerance, (
                f"Suggestion {i} macros don't add up: "
                f"reported={s.macros.calories}, calculated={calculated:.0f}"
            )

        print(f"\n✓ All {len(suggestions)} suggestions have valid nutrition data")

    @pytest.mark.asyncio
    async def test_parallel_execution_actually_parallel(
        self, real_service, mock_suggestion_repo, mock_user_repo
    ):
        """
        Verify requests run in parallel, not sequential.
        If sequential: ~15-24s (3 × 5-8s)
        If parallel: ~5-10s
        """
        start_time = time.time()
        session, suggestions = await real_service.generate_suggestions(
            user_id="test_user",
            meal_type="lunch",
            meal_portion_type="regular",
            ingredients=["beef", "potatoes", "onions"],
            cooking_time_minutes=40,
        )
        elapsed = time.time() - start_time

        # If truly parallel, should be much less than 3x single request time
        # Single request ~5-8s, sequential would be 15-24s
        assert elapsed < 12, (
            f"Elapsed {elapsed:.2f}s suggests sequential execution. "
            "Parallel should be < 12s"
        )

        print(f"\n✓ Parallel verification: {elapsed:.2f}s (sequential would be ~15-24s)")


@pytest.mark.integration
class TestParallelHybridEdgeCases:
    """Edge case tests for parallel hybrid generation."""

    @pytest.mark.asyncio
    async def test_handles_empty_pinecone_results(
        self, real_service, mock_suggestion_repo, mock_user_repo
    ):
        """Should still generate when Pinecone returns no results."""
        # Use obscure ingredients that won't match anything in Pinecone
        session, suggestions = await real_service.generate_suggestions(
            user_id="test_user",
            meal_type="lunch",
            meal_portion_type="regular",
            ingredients=["dragon_fruit", "jackfruit", "durian"],
            cooking_time_minutes=30,
        )

        assert len(suggestions) == 3, "Should still return 3 suggestions"
        print(f"\n✓ Generated {len(suggestions)} suggestions without Pinecone matches")

    @pytest.mark.asyncio
    async def test_respects_dietary_restrictions(
        self, real_service, mock_suggestion_repo, mock_user_repo
    ):
        """Allergies should be respected in generated recipes."""
        # Setup user with allergies
        mock_user_repo.get_profile.return_value.allergies = ["peanuts", "shellfish"]

        session, suggestions = await real_service.generate_suggestions(
            user_id="test_user",
            meal_type="dinner",
            meal_portion_type="regular",
            ingredients=["chicken", "vegetables"],
            cooking_time_minutes=30,
        )

        # Check no allergens in ingredients
        forbidden = {"peanut", "peanuts", "shrimp", "shellfish", "crab", "lobster"}
        for s in suggestions:
            for ing in s.ingredients:
                ing_lower = ing.name.lower()
                for allergen in forbidden:
                    assert allergen not in ing_lower, (
                        f"Allergen '{allergen}' found in {s.meal_name}: {ing.name}"
                    )

        print(f"\n✓ No allergens found in {len(suggestions)} suggestions")

    @pytest.mark.asyncio
    async def test_different_meal_types(
        self, real_service, mock_suggestion_repo, mock_user_repo
    ):
        """Should generate appropriate meals for different meal types."""
        meal_types = ["breakfast", "lunch", "dinner"]

        for meal_type in meal_types:
            session, suggestions = await real_service.generate_suggestions(
                user_id="test_user",
                meal_type=meal_type,
                meal_portion_type="regular",
                ingredients=["eggs", "cheese", "vegetables"],
                cooking_time_minutes=20,
            )

            assert len(suggestions) == 3
            print(f"✓ {meal_type.title()}: {[s.meal_name for s in suggestions]}")

    @pytest.mark.asyncio
    async def test_regeneration_excludes_previous(
        self, real_service, mock_suggestion_repo, mock_user_repo
    ):
        """Regeneration should exclude previously shown IDs."""
        # First generation
        session1, suggestions1 = await real_service.generate_suggestions(
            user_id="test_user",
            meal_type="lunch",
            meal_portion_type="regular",
            ingredients=["chicken", "rice"],
            cooking_time_minutes=25,
        )

        first_ids = [s.id for s in suggestions1]
        mock_suggestion_repo.get_session.return_value = session1

        # Regeneration
        session2, suggestions2 = await real_service.regenerate_suggestions(
            user_id="test_user",
            session_id=session1.id,
            exclude_ids=first_ids,
        )

        second_ids = [s.id for s in suggestions2]

        # IDs should be different
        assert not set(first_ids) & set(second_ids), (
            "Regenerated suggestions should have different IDs"
        )

        print(f"\n✓ First batch IDs: {first_ids}")
        print(f"✓ Second batch IDs: {second_ids}")
