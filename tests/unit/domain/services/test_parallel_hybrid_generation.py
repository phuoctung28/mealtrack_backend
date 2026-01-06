"""
Unit tests for parallel hybrid meal generation.
Tests the new parallel generation approach for faster meal suggestions.
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.model.meal_suggestion import (
    MacroEstimate,
    MealSuggestion,
    SuggestionSession,
    MealType,
)
from src.domain.services.meal_suggestion.suggestion_orchestration_service import (
    SuggestionOrchestrationService,
)
from src.domain.services.meal_suggestion.recipe_search_service import (
    RecipeSearchResult,
)
from src.domain.services.meal_suggestion.suggestion_prompt_builder import (
    build_single_meal_prompt,
)


@pytest.fixture
def mock_session():
    """Create a mock suggestion session."""
    return SuggestionSession(
        id="session_test123",
        user_id="user_123",
        meal_type="lunch",
        meal_portion_type="regular",
        target_calories=600,
        ingredients=["chicken", "rice", "broccoli", "garlic"],
        cooking_time_minutes=30,
        dietary_preferences=["high-protein"],
        allergies=["peanuts"],
    )


@pytest.fixture
def mock_recipe():
    """Create a mock recipe search result."""
    return RecipeSearchResult(
        recipe_id="recipe_001",
        name="Grilled Chicken with Rice",
        description="A healthy protein-packed meal",
        ingredients=[
            {"name": "chicken breast", "amount": 200, "unit": "g"},
            {"name": "rice", "amount": 100, "unit": "g"},
            {"name": "broccoli", "amount": 150, "unit": "g"},
        ],
        recipe_steps=[
            {"step": 1, "instruction": "Season chicken", "duration_minutes": 5},
            {"step": 2, "instruction": "Grill chicken", "duration_minutes": 15},
        ],
        seasonings=["salt", "pepper"],
        macros={"calories": 580, "protein": 45, "carbs": 50, "fat": 12},
        prep_time_minutes=25,
        confidence_score=0.85,
    )


@pytest.fixture
def mock_generation_service():
    """Create a mock meal generation service."""
    service = MagicMock()
    service.generate_meal_plan = MagicMock(return_value={
        "name": "Test Meal",
        "description": "A delicious test meal",
        "ingredients": [
            {"name": "chicken", "amount": 200, "unit": "g"},
            {"name": "rice", "amount": 100, "unit": "g"},
            {"name": "broccoli", "amount": 150, "unit": "g"},
        ],
        "recipe_steps": [
            {"step": 1, "instruction": "Season chicken with salt", "duration_minutes": 2},
            {"step": 2, "instruction": "Cook chicken until golden", "duration_minutes": 10},
            {"step": 3, "instruction": "Steam broccoli and serve", "duration_minutes": 5},
        ],
        "prep_time_minutes": 20,
    })
    return service


@pytest.fixture
def mock_suggestion_repo():
    """Create a mock suggestion repository."""
    repo = MagicMock()
    repo.save_session = AsyncMock()
    repo.save_suggestions = AsyncMock()
    repo.get_session = AsyncMock()
    repo.update_session = AsyncMock()
    return repo


@pytest.fixture
def mock_user_repo():
    """Create a mock user repository."""
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
def mock_recipe_search():
    """Create a mock recipe search service."""
    service = MagicMock()
    service.search_recipes = MagicMock(return_value=[])
    return service


@pytest.fixture
def mock_nutrition_enrichment():
    """Create a mock nutrition enrichment service."""
    service = MagicMock()
    enrichment_result = MagicMock()
    enrichment_result.macros = MacroEstimate(
        calories=580, protein=45, carbs=50, fat=12
    )
    enrichment_result.confidence_score = 0.9
    enrichment_result.missing_ingredients = []
    service.calculate_meal_nutrition = MagicMock(return_value=enrichment_result)
    return service


class TestBuildSingleMealPrompt:
    """Tests for build_single_meal_prompt function."""

    def test_includes_meal_type_and_calories(self, mock_session):
        """Prompt should include meal type and target calories."""
        prompt = build_single_meal_prompt(mock_session, meal_index=0)

        assert "lunch" in prompt.lower()
        assert "600" in prompt

    def test_includes_ingredients(self, mock_session):
        """Prompt should include user's ingredients."""
        prompt = build_single_meal_prompt(mock_session, meal_index=0)

        assert "chicken" in prompt.lower()
        assert "rice" in prompt.lower()

    def test_includes_allergies(self, mock_session):
        """Prompt should include allergy constraints."""
        prompt = build_single_meal_prompt(mock_session, meal_index=0)

        assert "AVOID" in prompt
        assert "peanuts" in prompt.lower()

    def test_includes_dietary_preferences(self, mock_session):
        """Prompt should include dietary preferences."""
        prompt = build_single_meal_prompt(mock_session, meal_index=0)

        assert "DIETARY" in prompt
        assert "high-protein" in prompt

    def test_variety_hints_differ_by_index(self, mock_session):
        """Different meal indices should get different style and naming hints."""
        prompt_0 = build_single_meal_prompt(mock_session, meal_index=0)
        prompt_1 = build_single_meal_prompt(mock_session, meal_index=1)
        prompt_2 = build_single_meal_prompt(mock_session, meal_index=2)

        # Style hints rotate per meal (Asian, Mediterranean, Classic)
        assert "Asian-inspired" in prompt_0
        assert "Mediterranean" in prompt_1
        assert "homestyle" in prompt_2

        # Naming hints also rotate
        assert "Herb-Crusted" in prompt_0
        assert "Golden" in prompt_1
        assert "Savory" in prompt_2

    def test_rotates_proteins_when_multiple_available(self):
        """When multiple proteins available, should rotate between them."""
        session = SuggestionSession(
            id="session_test",
            user_id="user_123",
            meal_type="lunch",
            meal_portion_type="regular",
            target_calories=900,
            ingredients=["chicken breast", "beef", "rice", "broccoli"],
            cooking_time_minutes=30,
        )

        prompt_0 = build_single_meal_prompt(session, meal_index=0)
        prompt_1 = build_single_meal_prompt(session, meal_index=1)
        prompt_2 = build_single_meal_prompt(session, meal_index=2)

        # Should rotate through proteins
        assert "chicken breast" in prompt_0
        assert "beef" in prompt_1
        assert "chicken breast" in prompt_2  # Wraps back to first protein

    def test_includes_inspiration_recipe(self, mock_session, mock_recipe):
        """Prompt should include inspiration recipe when provided."""
        prompt = build_single_meal_prompt(
            mock_session, meal_index=0, inspiration_recipe=mock_recipe
        )

        assert "INSPIRATION" in prompt
        assert mock_recipe.name in prompt

    def test_handles_missing_ingredients(self):
        """Prompt handles session with no ingredients."""
        session = SuggestionSession(
            id="session_test",
            user_id="user_123",
            meal_type="breakfast",
            meal_portion_type="light",
            target_calories=400,
            ingredients=[],
            cooking_time_minutes=15,
        )

        prompt = build_single_meal_prompt(session, meal_index=0)

        assert "common ingredients" in prompt.lower()


class TestParseSingleMeal:
    """Tests for _parse_single_meal method."""

    @pytest.fixture
    def service(
        self,
        mock_generation_service,
        mock_suggestion_repo,
        mock_user_repo,
        mock_recipe_search,
        mock_nutrition_enrichment,
    ):
        """Create orchestration service."""
        return SuggestionOrchestrationService(
            generation_service=mock_generation_service,
            suggestion_repo=mock_suggestion_repo,
            user_repo=mock_user_repo,
            recipe_search=mock_recipe_search,
            nutrition_enrichment=mock_nutrition_enrichment,
        )

    def test_parses_valid_meal_data(self, service, mock_session):
        """Should parse valid meal data into MealSuggestion."""
        meal_data = {
            "name": "Grilled Chicken Bowl",
            "description": "Healthy protein meal",
            "ingredients": [
                {"name": "chicken", "amount": 200, "unit": "g"},
                {"name": "rice", "amount": 100, "unit": "g"},
                {"name": "broccoli", "amount": 150, "unit": "g"},
            ],
            "recipe_steps": [
                {"step": 1, "instruction": "Season chicken", "duration_minutes": 2},
                {"step": 2, "instruction": "Grill chicken", "duration_minutes": 10},
                {"step": 3, "instruction": "Serve with sides", "duration_minutes": 3},
            ],
            "prep_time_minutes": 20,
        }

        result = service._parse_single_meal(meal_data, mock_session, index=0)

        assert result.meal_name == "Grilled Chicken Bowl"
        assert result.session_id == mock_session.id
        assert len(result.ingredients) == 3
        assert len(result.recipe_steps) == 3

    def test_returns_none_for_incomplete_data(self, service, mock_session):
        """Should return None when ingredients or steps are missing."""
        # Missing ingredients
        meal_data = {
            "name": "Test Meal",
            "description": "Some meal",
            "ingredients": [],
            "recipe_steps": [
                {"step": 1, "instruction": "Do something", "duration_minutes": 5},
                {"step": 2, "instruction": "Do more", "duration_minutes": 5},
            ],
        }
        result = service._parse_single_meal(meal_data, mock_session, index=1)
        assert result is None

        # Missing recipe_steps
        meal_data2 = {
            "name": "Test Meal",
            "description": "Some meal",
            "ingredients": [
                {"name": "chicken", "amount": 200, "unit": "g"},
                {"name": "rice", "amount": 100, "unit": "g"},
            ],
            "recipe_steps": [],
        }
        result2 = service._parse_single_meal(meal_data2, mock_session, index=2)
        assert result2 is None


class TestGenerateParallelHybrid:
    """Tests for _generate_parallel_hybrid method."""

    @pytest.fixture
    def service(
        self,
        mock_generation_service,
        mock_suggestion_repo,
        mock_user_repo,
        mock_recipe_search,
        mock_nutrition_enrichment,
    ):
        """Create orchestration service."""
        return SuggestionOrchestrationService(
            generation_service=mock_generation_service,
            suggestion_repo=mock_suggestion_repo,
            user_repo=mock_user_repo,
            recipe_search=mock_recipe_search,
            nutrition_enrichment=mock_nutrition_enrichment,
        )

    @pytest.mark.asyncio
    async def test_generates_3_meals(self, service, mock_session):
        """Should generate exactly 3 meals."""
        suggestions = await service._generate_parallel_hybrid(mock_session, [])

        assert len(suggestions) == 3

    @pytest.mark.asyncio
    async def test_calls_ai_generation_3_times(self, service, mock_session):
        """Should make 3 parallel AI calls."""
        await service._generate_parallel_hybrid(mock_session, [])

        assert service._generation.generate_meal_plan.call_count == 3

    @pytest.mark.asyncio
    async def test_enriches_nutrition(self, service, mock_session):
        """Should enrich all meals with nutrition data."""
        suggestions = await service._generate_parallel_hybrid(mock_session, [])

        # All 3 meals should have enriched macros
        assert service._nutrition_enrichment.calculate_meal_nutrition.call_count == 3
        for s in suggestions:
            assert s.macros.calories > 0

    @pytest.mark.asyncio
    async def test_uses_pinecone_inspiration(
        self, service, mock_session, mock_recipe
    ):
        """Should use Pinecone recipes as inspiration."""
        service._recipe_search.search_recipes.return_value = [
            mock_recipe,
            mock_recipe,
            mock_recipe,
        ]

        await service._generate_parallel_hybrid(mock_session, [])

        service._recipe_search.search_recipes.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_partial_failures(self, service, mock_session):
        """Should return fallbacks for failed generations."""
        # First call succeeds with complete data, others fail
        service._generation.generate_meal_plan.side_effect = [
            {
                "name": "Success Meal",
                "description": "Works",
                "ingredients": [
                    {"name": "chicken", "amount": 200, "unit": "g"},
                    {"name": "rice", "amount": 100, "unit": "g"},
                ],
                "recipe_steps": [
                    {"step": 1, "instruction": "Season chicken", "duration_minutes": 2},
                    {"step": 2, "instruction": "Cook chicken", "duration_minutes": 10},
                ],
            },
            Exception("API Error"),
            Exception("Timeout"),
        ]

        suggestions = await service._generate_parallel_hybrid(mock_session, [])

        assert len(suggestions) == 3
        # With parallel execution, order isn't guaranteed - check content not position
        meal_names = [s.meal_name for s in suggestions]
        suggestion_ids = [s.id for s in suggestions]

        # One should be the success meal
        assert any("Success Meal" in name for name in meal_names)
        # Two should be fallbacks
        fallback_count = sum(1 for sid in suggestion_ids if "fallback" in sid)
        assert fallback_count == 2

    @pytest.mark.asyncio
    async def test_excludes_recipe_ids(self, service, mock_session, mock_recipe):
        """Should pass exclude_ids to recipe search."""
        exclude_ids = ["recipe_001", "recipe_002"]

        await service._generate_parallel_hybrid(mock_session, exclude_ids)

        call_args = service._recipe_search.search_recipes.call_args
        assert call_args is not None
        criteria = call_args.kwargs["criteria"]
        assert criteria.exclude_ids == exclude_ids


class TestParallelExecutionTiming:
    """Tests verifying parallel execution behavior."""

    @pytest.fixture
    def slow_generation_service(self):
        """Create a service with simulated latency."""
        service = MagicMock()

        def slow_generate(*args, **kwargs):
            """Simulate API latency."""
            time.sleep(0.1)  # 100ms per call
            return {
                "name": "Test Meal",
                "description": "Generated",
                "ingredients": [
                    {"name": "chicken", "amount": 200, "unit": "g"},
                    {"name": "rice", "amount": 100, "unit": "g"},
                ],
                "recipe_steps": [
                    {"step": 1, "instruction": "Season chicken", "duration_minutes": 2},
                    {"step": 2, "instruction": "Cook chicken", "duration_minutes": 10},
                ],
            }

        service.generate_meal_plan = slow_generate
        return service

    @pytest.mark.asyncio
    async def test_parallel_execution_faster_than_sequential(
        self,
        slow_generation_service,
        mock_suggestion_repo,
        mock_user_repo,
        mock_recipe_search,
        mock_nutrition_enrichment,
        mock_session,
    ):
        """Parallel execution should be faster than 3x sequential time."""
        service = SuggestionOrchestrationService(
            generation_service=slow_generation_service,
            suggestion_repo=mock_suggestion_repo,
            user_repo=mock_user_repo,
            recipe_search=mock_recipe_search,
            nutrition_enrichment=mock_nutrition_enrichment,
        )

        start = time.time()
        await service._generate_parallel_hybrid(mock_session, [])
        elapsed = time.time() - start

        # Sequential would be ~300ms (3 × 100ms)
        # Parallel should be ~100-150ms
        # Allow some margin for overhead
        assert elapsed < 0.25, f"Execution took {elapsed:.3f}s, expected < 0.25s"
