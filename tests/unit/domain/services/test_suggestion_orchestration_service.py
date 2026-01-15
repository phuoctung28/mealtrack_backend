"""
Unit tests for SuggestionOrchestrationService's direct generation pipeline.
Tests the streamlined 2-phase generation process:
- Phase 1: Generation of 4 diverse meal names.
- Phase 2: Parallel generation of 4 recipes from those names.
- Direct generation in the target language is tested.
- Error handling for insufficient name/recipe generation is tested.
"""
import asyncio
from unittest.mock import Mock, AsyncMock, call

import pytest

from src.domain.model.meal_suggestion import SuggestionSession, MealSuggestion, MealType, MacroEstimate, Ingredient, RecipeStep
from src.domain.schemas.meal_generation_schemas import MealNamesResponse, RecipeDetailsResponse
from src.domain.services.meal_suggestion.suggestion_orchestration_service import SuggestionOrchestrationService

# Fixtures for mocked dependencies
@pytest.fixture
def mock_generation_service():
    """Mock MealGenerationServicePort."""
    return Mock()

@pytest.fixture
def mock_suggestion_repo():
    """Mock MealSuggestionRepositoryPort."""
    repo = AsyncMock()
    repo.get_session.return_value = None
    return repo

@pytest.fixture
def mock_user_repo():
    """Mock UserRepositoryPort."""
    profile_mock = Mock()
    profile_mock.gender = "female"
    profile_mock.age = 30
    profile_mock.height_cm = 165
    profile_mock.weight_kg = 60
    profile_mock.activity_level = "moderate"
    profile_mock.fitness_goal = "cut"
    profile_mock.body_fat_percentage = 25
    profile_mock.dietary_preferences = ["vegetarian"]
    profile_mock.allergies = ["peanuts"]
    profile_mock.meals_per_day = 3
    
    user_repo_mock = Mock()
    user_repo_mock.get_profile.return_value = profile_mock
    return user_repo_mock

@pytest.fixture
def redis_client():
    """Fixture for a mock redis client."""
    client = AsyncMock()
    client.get.return_value = None  # Cache miss by default
    return client

@pytest.fixture
def orchestration_service(mock_generation_service, mock_suggestion_repo, mock_user_repo, redis_client):
    """Create SuggestionOrchestrationService with mocked dependencies."""
    return SuggestionOrchestrationService(
        generation_service=mock_generation_service,
        suggestion_repo=mock_suggestion_repo,
        user_repo=mock_user_repo,
        redis_client=redis_client,
    )

# Fixtures for test data
@pytest.fixture
def mock_session():
    """Create a test session."""
    return SuggestionSession(
        id="test_session_123",
        user_id="user_456",
        meal_type="breakfast",
        meal_portion_type="standard",
        target_calories=500,
        ingredients=["eggs", "spinach"],
        cooking_time_minutes=15,
        language="en",
        dietary_preferences=["vegetarian"],
        allergies=["peanuts"],
    )

@pytest.fixture
def mock_recipe_response():
    """Create a valid RecipeDetailsResponse mock content."""
    return {
        "ingredients": [{"name": "Spinach", "amount": 1, "unit": "cup"}],
        "recipe_steps": [{"step": 1, "instruction": "Wilt spinach", "duration_minutes": 5}],
        "prep_time_minutes": 10,
    }

# Main Test Class
@pytest.mark.asyncio
class TestSuggestionGenerationPipeline:

    async def test_successful_generation_flow(self, orchestration_service, mock_session, mock_recipe_response):
        """
        Tests the ideal end-to-end flow:
        1. 4 unique names are generated.
        2. 4 recipe generations are started in parallel.
        3. At least 3 recipes are successfully generated.
        4. The service returns the 3 successful suggestions.
        """
        # --- Mocking Phase 1: Name Generation ---
        mock_names = {"meal_names": ["Spinach Omelette", "Tofu Scramble", "Green Smoothie", "Avocado Toast"]}
        
        # --- Mocking Phase 2: Recipe Generation ---
        # Simulate 3 successful recipe generations and 1 failure
        orchestration_service._generation.generate_meal_plan.side_effect = [
            mock_names,
            mock_recipe_response,
            mock_recipe_response,
            mock_recipe_response,
            None  # The 4th call fails
        ]

        # --- Execute ---
        suggestions = await orchestration_service._generate_parallel_hybrid(
            session=mock_session,
            exclude_meal_names=[]
        )

        # --- Assertions ---
        assert len(suggestions) == 3
        assert all(isinstance(s, MealSuggestion) for s in suggestions)
        
        # Check that 1 call for names + 4 calls for recipes were made
        assert orchestration_service._generation.generate_meal_plan.call_count == 5

    async def test_failure_if_not_enough_names_generated(self, orchestration_service, mock_session):
        """
        Tests that the process fails if Phase 1 does not return enough unique meal names.
        This replaces the old fallback tests.
        """
        # --- Mocking ---
        # Simulate the LLM returning fewer than the required number of names
        mock_names = {"meal_names": ["Spinach Omelette", "Tofu Scramble"]}
        orchestration_service._generation.generate_meal_plan.return_value = mock_names

        # --- Execute & Assert ---
        with pytest.raises(RuntimeError, match="Could not generate enough unique meal names"):
            await orchestration_service._generate_parallel_hybrid(
                session=mock_session,
                exclude_meal_names=[]
            )

    async def test_failure_if_not_enough_recipes_generated(self, orchestration_service, mock_session):
        """
        Tests that the process fails if Phase 2 does not generate the minimum number of recipes.
        This replaces the old partial results tests.
        """
        # --- Mocking ---
        mock_names = {"meal_names": ["Spinach Omelette", "Tofu Scramble", "Green Smoothie", "Avocado Toast"]}
        
        # Simulate only one successful recipe generation
        orchestration_service._generation.generate_meal_plan.side_effect = [
            mock_names,
            None, # Fail
            None, # Fail
            {"ingredients": [], "recipe_steps": [], "prep_time_minutes": 0}, # Fail (invalid data)
            None  # Fail
        ]

        # --- Execute & Assert ---
        with pytest.raises(RuntimeError, match="Failed to generate any recipes"):
            await orchestration_service._generate_parallel_hybrid(
                session=mock_session,
                exclude_meal_names=[]
            )

    async def test_direct_language_generation_prompts(self, orchestration_service, mock_session, mock_recipe_response):
        """
        Tests that the system prompts correctly instruct the LLM to generate content
        directly in the requested non-English language, while keeping JSON keys in English.
        """
        # --- Setup ---
        mock_session.language = "vi" # Vietnamese
        target_lang_name = "Vietnamese"
        
        mock_names = {"meal_names": ["Cháo yến mạch", "Trứng bác đậu phụ", "Sinh tố xanh", "Bánh mì bơ"]}
        orchestration_service._generation.generate_meal_plan.side_effect = [
            mock_names,
            mock_recipe_response, mock_recipe_response, mock_recipe_response, mock_recipe_response
        ]

        # --- Execute ---
        await orchestration_service._generate_parallel_hybrid(
            session=mock_session,
            exclude_meal_names=[]
        )

        # --- Assertions ---
        # Get all the calls made to the generation service
        all_calls = orchestration_service._generation.generate_meal_plan.call_args_list

        # 1. Check the system prompt for name generation (first call)
        name_gen_system_prompt = all_calls[0].args[1]
        assert f"Output content in {target_lang_name}" in name_gen_system_prompt
        assert "Keep all JSON keys (like 'meal_names') in English" in name_gen_system_prompt

        # 2. Check the system prompt for recipe generation (second call)
        recipe_gen_system_prompt = all_calls[1].args[1]
        assert f"Output string values in {target_lang_name}" in recipe_gen_system_prompt
        assert "JSON KEYS (e.g., 'ingredients', 'recipe_steps', 'amount', 'unit') MUST BE IN ENGLISH" in recipe_gen_system_prompt

    def test_constants_are_set_correctly(self, orchestration_service):
        """Ensures performance-related constants are set to their expected optimized values."""
        assert orchestration_service.SUGGESTIONS_COUNT == 3
        assert orchestration_service.MIN_ACCEPTABLE_RESULTS == 2
        assert orchestration_service.PARALLEL_SINGLE_MEAL_TIMEOUT == 20
        assert orchestration_service.PARALLEL_STAGGER_MS == 200