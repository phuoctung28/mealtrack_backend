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
from src.domain.services.meal_suggestion.parallel_recipe_generator import ParallelRecipeGenerator
from src.domain.services.meal_suggestion.recipe_attempt_builder import PARALLEL_SINGLE_MEAL_TIMEOUT

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
    profile_mock.job_type = "desk"
    profile_mock.training_days_per_week = 4
    profile_mock.training_minutes_per_session = 60
    profile_mock.fitness_goal = "cut"
    profile_mock.body_fat_percentage = 25
    profile_mock.dietary_preferences = ["vegetarian"]
    profile_mock.allergies = ["peanuts"]
    profile_mock.meals_per_day = 3

    user_repo_mock = Mock()
    user_repo_mock.get_profile.return_value = profile_mock
    return user_repo_mock

@pytest.fixture
def recipe_generator(mock_generation_service):
    """Create ParallelRecipeGenerator with mocked dependencies."""
    from src.domain.services.meal_suggestion.translation_service import TranslationService
    from src.domain.services.meal_suggestion.macro_validation_service import MacroValidationService
    return ParallelRecipeGenerator(
        generation_service=mock_generation_service,
        translation_service=TranslationService(mock_generation_service),
        macro_validator=MacroValidationService(),
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
        "ingredients": [
            {"name": "Spinach", "amount": 1, "unit": "cup"},
            {"name": "Eggs", "amount": 2, "unit": "whole"},
        ],
        "recipe_steps": [{"step": 1, "instruction": "Wilt spinach", "duration_minutes": 5}],
        "prep_time_minutes": 10,
    }

# Main Test Class
@pytest.mark.asyncio
class TestSuggestionGenerationPipeline:

    async def test_successful_generation_flow(self, recipe_generator, mock_generation_service, mock_session, mock_recipe_response):
        """
        Tests the ideal end-to-end flow:
        1. 4 unique names are generated.
        2. 4 recipe generations are started in parallel.
        3. At least 3 recipes are successfully generated.
        4. The service returns the 3 successful suggestions.
        """
        mock_names = {"meal_names": ["Spinach Omelette", "Tofu Scramble", "Green Smoothie", "Avocado Toast"]}

        mock_generation_service.generate_meal_plan.side_effect = [
            mock_names,
            mock_recipe_response,
            mock_recipe_response,
            mock_recipe_response,
            None,
            None,
        ]

        suggestions = await recipe_generator.generate(
            session=mock_session,
            exclude_meal_names=[]
        )

        assert len(suggestions) == 3
        assert all(isinstance(s, MealSuggestion) for s in suggestions)

        call_count = mock_generation_service.generate_meal_plan.call_count
        assert 5 <= call_count <= 6, f"Expected 5-6 calls, got {call_count}"

    async def test_failure_if_not_enough_names_generated(self, recipe_generator, mock_generation_service, mock_session):
        """
        Tests that the process fails if Phase 1 does not return enough unique meal names.
        """
        mock_names = {"meal_names": ["Spinach Omelette", "Tofu Scramble"]}
        mock_generation_service.generate_meal_plan.return_value = mock_names

        with pytest.raises(RuntimeError, match="Could not generate enough unique meal names"):
            await recipe_generator.generate(
                session=mock_session,
                exclude_meal_names=[]
            )

    async def test_failure_if_not_enough_recipes_generated(self, recipe_generator, mock_generation_service, mock_session):
        """
        Tests that the process fails if Phase 2 does not generate the minimum number of recipes.
        """
        mock_names = {"meal_names": ["Spinach Omelette", "Tofu Scramble", "Green Smoothie", "Avocado Toast"]}

        mock_generation_service.generate_meal_plan.side_effect = [
            mock_names,
            None,
            None,
            {"ingredients": [], "recipe_steps": [], "prep_time_minutes": 0},
            None
        ]

        with pytest.raises(RuntimeError, match="Failed to generate any recipes"):
            await recipe_generator.generate(
                session=mock_session,
                exclude_meal_names=[]
            )

    async def test_direct_language_generation_prompts(self, recipe_generator, mock_generation_service, mock_session, mock_recipe_response):
        """
        Tests that the system prompts correctly instruct the LLM to generate content
        directly in the requested non-English language, while keeping JSON keys in English.
        """
        mock_session.language = "vi"
        target_lang_name = "Vietnamese"

        mock_names = {"meal_names": ["Cháo yến mạch", "Trứng bác đậu phụ", "Sinh tố xanh", "Bánh mì bơ"]}
        mock_generation_service.generate_meal_plan.side_effect = [
            mock_names,
            mock_recipe_response, mock_recipe_response, mock_recipe_response, mock_recipe_response
        ]

        await recipe_generator.generate(
            session=mock_session,
            exclude_meal_names=[]
        )

        all_calls = mock_generation_service.generate_meal_plan.call_args_list

        # Check name generation system prompt
        name_gen_system_prompt = all_calls[0].args[1]
        assert f"Output content in {target_lang_name}" in name_gen_system_prompt
        assert "Keep all JSON keys (like 'meal_names') in English" in name_gen_system_prompt

        # Check recipe generation system prompt
        recipe_gen_system_prompt = all_calls[1].args[1]
        assert f"Output string values in {target_lang_name}" in recipe_gen_system_prompt
        assert "JSON keys MUST be in English" in recipe_gen_system_prompt

    def test_constants_are_set_correctly(self, recipe_generator):
        """Ensures performance-related constants are set to their expected optimized values."""
        assert recipe_generator.SUGGESTIONS_COUNT == 3
        assert recipe_generator.MIN_ACCEPTABLE_RESULTS == 2
        assert PARALLEL_SINGLE_MEAL_TIMEOUT == 35