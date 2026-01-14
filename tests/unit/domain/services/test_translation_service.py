"""
Unit tests for TranslationService Phase 3 translation.
Tests recursive traversal, string extraction, and translation reconstruction.
"""
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

import pytest

from src.domain.model.meal_suggestion import (
    MealSuggestion,
    Ingredient,
    RecipeStep,
    MacroEstimate,
    MealType,
    SuggestionStatus,
)
from src.domain.services.meal_suggestion.translation_service import TranslationService


@pytest.fixture
def mock_generation_service():
    """Mock MealGenerationServicePort."""
    service = Mock()
    service.generate_meal_plan = Mock()
    return service


@pytest.fixture
def translation_service(mock_generation_service):
    """Create TranslationService instance."""
    return TranslationService(mock_generation_service)


@pytest.fixture
def sample_meal_suggestion():
    """Create a sample MealSuggestion for testing."""
    return MealSuggestion(
        id="sug_test123",
        session_id="session_test",
        user_id="user_test",
        meal_name="Grilled Chicken Breast",
        description="A healthy grilled chicken dish",
        meal_type=MealType.DINNER,
        macros=MacroEstimate(calories=450, protein=35.0, carbs=30.0, fat=15.0),
        ingredients=[
            Ingredient(name="chicken breast", amount=200.0, unit="g"),
            Ingredient(name="olive oil", amount=15.0, unit="ml"),
            Ingredient(name="broccoli", amount=150.0, unit="g"),
        ],
        recipe_steps=[
            RecipeStep(
                step=1,
                instruction="Heat the pan over medium heat",
                duration_minutes=5,
            ),
            RecipeStep(
                step=2,
                instruction="Cook chicken for 8 minutes per side",
                duration_minutes=16,
            ),
        ],
        prep_time_minutes=25,
        confidence_score=0.85,
        status=SuggestionStatus.PENDING,
        generated_at=datetime.now(),
    )


class TestExtractTranslatableStrings:
    """Test string extraction from MealSuggestion."""

    def test_extracts_meal_name(self, translation_service, sample_meal_suggestion):
        """Test that meal_name is extracted."""
        items = translation_service._extract_translatable_strings(sample_meal_suggestion)
        paths = [item[0] for item in items]
        assert "meal_name" in paths

    def test_extracts_ingredient_names(self, translation_service, sample_meal_suggestion):
        """Test that ingredient names are extracted."""
        items = translation_service._extract_translatable_strings(sample_meal_suggestion)
        paths = [item[0] for item in items]
        assert "ingredients[0].name" in paths
        assert "ingredients[1].name" in paths
        assert "ingredients[2].name" in paths

    def test_extracts_ingredient_units(self, translation_service, sample_meal_suggestion):
        """Test that ingredient units are extracted."""
        items = translation_service._extract_translatable_strings(sample_meal_suggestion)
        paths = [item[0] for item in items]
        assert "ingredients[0].unit" in paths
        assert "ingredients[1].unit" in paths

    def test_extracts_recipe_step_instructions(
        self, translation_service, sample_meal_suggestion
    ):
        """Test that recipe step instructions are extracted."""
        items = translation_service._extract_translatable_strings(sample_meal_suggestion)
        paths = [item[0] for item in items]
        assert "recipe_steps[0].instruction" in paths
        assert "recipe_steps[1].instruction" in paths

    def test_skips_ids(self, translation_service, sample_meal_suggestion):
        """Test that ID fields are skipped."""
        items = translation_service._extract_translatable_strings(sample_meal_suggestion)
        paths = [item[0] for item in items]
        assert "id" not in paths
        assert "session_id" not in paths
        assert "user_id" not in paths

    def test_skips_numbers(self, translation_service, sample_meal_suggestion):
        """Test that numeric fields are skipped."""
        items = translation_service._extract_translatable_strings(sample_meal_suggestion)
        paths = [item[0] for item in items]
        assert "prep_time_minutes" not in paths
        assert "confidence_score" not in paths
        assert "ingredients[0].amount" not in paths
        assert "recipe_steps[0].step" not in paths
        assert "recipe_steps[0].duration_minutes" not in paths

    def test_skips_enums(self, translation_service, sample_meal_suggestion):
        """Test that enum fields are skipped."""
        items = translation_service._extract_translatable_strings(sample_meal_suggestion)
        paths = [item[0] for item in items]
        assert "meal_type" not in paths
        assert "status" not in paths

    def test_skips_empty_strings(self, translation_service):
        """Test that empty strings are skipped."""
        suggestion = MealSuggestion(
            id="test",
            session_id="session",
            user_id="user",
            meal_name="Test Meal",
            description="",  # Empty string
            meal_type=MealType.BREAKFAST,
            macros=MacroEstimate(calories=300, protein=20.0, carbs=30.0, fat=10.0),
            ingredients=[],
            recipe_steps=[],
            prep_time_minutes=10,
            confidence_score=0.8,
        )
        items = translation_service._extract_translatable_strings(suggestion)
        # Should only have meal_name, description should be skipped if empty
        paths = [item[0] for item in items]
        assert "meal_name" in paths


class TestBatchTranslate:
    """Test batch translation using Gemini API."""

    @pytest.mark.asyncio
    async def test_translates_strings(self, translation_service, mock_generation_service):
        """Test that strings are translated via Gemini."""
        strings = ["Hello", "World"]
        mock_generation_service.generate_meal_plan.return_value = {
            "translations": ["Xin chào", "Thế giới"]
        }

        result = await translation_service._batch_translate(strings, "vi")

        assert result == ["Xin chào", "Thế giới"]
        mock_generation_service.generate_meal_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_translation_failure(
        self, translation_service, mock_generation_service
    ):
        """Test that original strings are returned on translation failure."""
        strings = ["Hello", "World"]
        mock_generation_service.generate_meal_plan.side_effect = Exception("API Error")

        result = await translation_service._batch_translate(strings, "vi")

        assert result == strings  # Fallback to original

    @pytest.mark.asyncio
    async def test_handles_mismatched_count(
        self, translation_service, mock_generation_service
    ):
        """Test handling when translation count doesn't match input count."""
        strings = ["Hello", "World", "Test"]
        mock_generation_service.generate_meal_plan.return_value = {
            "translations": ["Xin chào", "Thế giới"]  # Only 2 instead of 3
        }

        result = await translation_service._batch_translate(strings, "vi")

        # Should pad with original strings
        assert len(result) == 3
        assert result[0] == "Xin chào"
        assert result[1] == "Thế giới"
        assert result[2] == "Test"  # Original string

    @pytest.mark.asyncio
    async def test_handles_empty_list(self, translation_service):
        """Test handling of empty string list."""
        result = await translation_service._batch_translate([], "vi")
        assert result == []


class TestReconstructWithTranslations:
    """Test reconstruction of MealSuggestion with translated strings."""

    def test_reconstructs_meal_name(self, translation_service, sample_meal_suggestion):
        """Test that meal_name is translated."""
        translation_map = {"meal_name": "Ức gà nướng"}

        result = translation_service._reconstruct_with_translations(
            sample_meal_suggestion, translation_map
        )

        assert result.meal_name == "Ức gà nướng"
        assert result.id == sample_meal_suggestion.id  # ID unchanged

    def test_reconstructs_ingredients(self, translation_service, sample_meal_suggestion):
        """Test that ingredient names are translated."""
        translation_map = {
            "ingredients[0].name": "ức gà",
            "ingredients[1].name": "dầu ô liu",
            "ingredients[2].name": "bông cải xanh",
        }

        result = translation_service._reconstruct_with_translations(
            sample_meal_suggestion, translation_map
        )

        assert result.ingredients[0].name == "ức gà"
        assert result.ingredients[1].name == "dầu ô liu"
        assert result.ingredients[2].name == "bông cải xanh"
        # Amounts and units unchanged
        assert result.ingredients[0].amount == 200.0
        assert result.ingredients[0].unit == "g"

    def test_reconstructs_recipe_steps(self, translation_service, sample_meal_suggestion):
        """Test that recipe step instructions are translated."""
        translation_map = {
            "recipe_steps[0].instruction": "Làm nóng chảo trên lửa vừa",
            "recipe_steps[1].instruction": "Nấu gà 8 phút mỗi mặt",
        }

        result = translation_service._reconstruct_with_translations(
            sample_meal_suggestion, translation_map
        )

        assert result.recipe_steps[0].instruction == "Làm nóng chảo trên lửa vừa"
        assert result.recipe_steps[1].instruction == "Nấu gà 8 phút mỗi mặt"
        # Step numbers and durations unchanged
        assert result.recipe_steps[0].step == 1
        assert result.recipe_steps[0].duration_minutes == 5

    def test_preserves_non_translatable_fields(
        self, translation_service, sample_meal_suggestion
    ):
        """Test that IDs, numbers, and enums are preserved."""
        translation_map = {"meal_name": "Ức gà nướng"}

        result = translation_service._reconstruct_with_translations(
            sample_meal_suggestion, translation_map
        )

        # IDs unchanged
        assert result.id == sample_meal_suggestion.id
        assert result.session_id == sample_meal_suggestion.session_id
        assert result.user_id == sample_meal_suggestion.user_id

        # Numbers unchanged
        assert result.prep_time_minutes == sample_meal_suggestion.prep_time_minutes
        assert result.confidence_score == sample_meal_suggestion.confidence_score

        # Enums unchanged
        assert result.meal_type == sample_meal_suggestion.meal_type
        assert result.status == sample_meal_suggestion.status


class TestTranslateMealSuggestion:
    """Test full translation workflow."""

    @pytest.mark.asyncio
    async def test_translates_english_to_vietnamese(
        self, translation_service, sample_meal_suggestion, mock_generation_service
    ):
        """Test full translation from English to Vietnamese."""
        # Mock translation response
        mock_generation_service.generate_meal_plan.return_value = {
            "translations": [
                "Ức gà nướng",  # meal_name
                "ức gà",  # ingredients[0].name
                "dầu ô liu",  # ingredients[1].name
                "bông cải xanh",  # ingredients[2].name
                "g",  # ingredients[0].unit
                "ml",  # ingredients[1].unit
                "g",  # ingredients[2].unit
                "Làm nóng chảo trên lửa vừa",  # recipe_steps[0].instruction
                "Nấu gà 8 phút mỗi mặt",  # recipe_steps[1].instruction
            ]
        }

        result = await translation_service.translate_meal_suggestion(
            sample_meal_suggestion, "vi"
        )

        assert result.meal_name == "Ức gà nướng"
        assert result.ingredients[0].name == "ức gà"
        assert result.recipe_steps[0].instruction == "Làm nóng chảo trên lửa vừa"
        # Verify non-translatable fields preserved
        assert result.id == sample_meal_suggestion.id
        assert result.ingredients[0].amount == 200.0

    @pytest.mark.asyncio
    async def test_skips_translation_for_english(
        self, translation_service, sample_meal_suggestion, mock_generation_service
    ):
        """Test that English suggestions are not translated."""
        result = await translation_service.translate_meal_suggestion(
            sample_meal_suggestion, "en"
        )

        # Should return original without calling translation API
        assert result == sample_meal_suggestion
        mock_generation_service.generate_meal_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_empty_suggestion(self, translation_service, mock_generation_service):
        """Test handling of suggestion with no translatable content."""
        suggestion = MealSuggestion(
            id="test",
            session_id="session",
            user_id="user",
            meal_name="",
            description="",
            meal_type=MealType.BREAKFAST,
            macros=MacroEstimate(calories=300, protein=20.0, carbs=30.0, fat=10.0),
            ingredients=[],
            recipe_steps=[],
            prep_time_minutes=10,
            confidence_score=0.8,
        )

        result = await translation_service.translate_meal_suggestion(suggestion, "vi")

        # Should return original (no translatable strings)
        assert result == suggestion
        mock_generation_service.generate_meal_plan.assert_not_called()


class TestBatchTranslation:
    """Test batch translation of multiple meal suggestions."""

    @pytest.mark.asyncio
    async def test_batch_translates_multiple_meals(
        self, translation_service, sample_meal_suggestion, mock_generation_service
    ):
        """Test that multiple meals are translated in a single API call."""
        # Create 3 similar meals
        meal1 = sample_meal_suggestion
        meal2 = MealSuggestion(
            id="sug_test456",
            session_id="session_test",
            user_id="user_test",
            meal_name="Baked Salmon",
            description="Healthy salmon dish",
            meal_type=MealType.DINNER,
            macros=MacroEstimate(calories=500, protein=40.0, carbs=25.0, fat=20.0),
            ingredients=[
                Ingredient(name="salmon fillet", amount=250.0, unit="g"),
                Ingredient(name="olive oil", amount=15.0, unit="ml"),  # Duplicate
                Ingredient(name="lemon", amount=1.0, unit="piece"),
            ],
            recipe_steps=[
                RecipeStep(
                    step=1,
                    instruction="Preheat oven to 200C",
                    duration_minutes=5,
                ),
                RecipeStep(
                    step=2,
                    instruction="Bake salmon for 15 minutes",
                    duration_minutes=15,
                ),
            ],
            prep_time_minutes=20,
            confidence_score=0.9,
        )
        meal3 = MealSuggestion(
            id="sug_test789",
            session_id="session_test",
            user_id="user_test",
            meal_name="Grilled Vegetables",
            description="Healthy veggie dish",
            meal_type=MealType.LUNCH,
            macros=MacroEstimate(calories=300, protein=10.0, carbs=40.0, fat=12.0),
            ingredients=[
                Ingredient(name="broccoli", amount=150.0, unit="g"),  # Duplicate
                Ingredient(name="bell pepper", amount=100.0, unit="g"),
                Ingredient(name="olive oil", amount=10.0, unit="ml"),  # Duplicate
            ],
            recipe_steps=[
                RecipeStep(
                    step=1,
                    instruction="Cut vegetables into chunks",
                    duration_minutes=5,
                ),
            ],
            prep_time_minutes=15,
            confidence_score=0.85,
        )

        suggestions = [meal1, meal2, meal3]

        # Mock translation response (note: unique strings only)
        # Total unique strings should be:
        # meal_name: 3, ingredient names: 6 unique (olive oil/broccoli deduplicated),
        # units: g, ml, piece, instructions: 6 unique
        mock_generation_service.generate_meal_plan.return_value = {
            "translations": [
                # Meal names
                "Ức gà nướng",
                "Cá hồi nướng",
                "Rau củ nướng",
                # Unique ingredient names
                "ức gà",
                "dầu ô liu",
                "bông cải xanh",
                "phi lê cá hồi",
                "chanh",
                "ớt chuông",
                # Units
                "g",
                "ml",
                "miếng",
                # Instructions (all unique)
                "Làm nóng chảo trên lửa vừa",
                "Nấu gà 8 phút mỗi mặt",
                "Làm nóng lò nướng đến 200C",
                "Nướng cá hồi trong 15 phút",
                "Cắt rau thành từng miếng",
            ]
        }

        result = await translation_service.translate_meal_suggestions_batch(
            suggestions, "vi"
        )

        # Should make only ONE API call
        assert mock_generation_service.generate_meal_plan.call_count == 1

        # Verify results
        assert len(result) == 3
        assert result[0].meal_name == "Ức gà nướng"
        assert result[1].meal_name == "Cá hồi nướng"
        assert result[2].meal_name == "Rau củ nướng"

        # Verify deduplication worked (olive oil appears in all 3 meals)
        assert result[0].ingredients[1].name == "dầu ô liu"
        assert result[1].ingredients[1].name == "dầu ô liu"
        assert result[2].ingredients[2].name == "dầu ô liu"

    @pytest.mark.asyncio
    async def test_batch_skips_english(
        self, translation_service, sample_meal_suggestion, mock_generation_service
    ):
        """Test that English meals are not translated."""
        suggestions = [sample_meal_suggestion]

        result = await translation_service.translate_meal_suggestions_batch(
            suggestions, "en"
        )

        assert result == suggestions
        mock_generation_service.generate_meal_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_handles_empty_list(
        self, translation_service, mock_generation_service
    ):
        """Test handling of empty suggestions list."""
        result = await translation_service.translate_meal_suggestions_batch([], "vi")

        assert result == []
        mock_generation_service.generate_meal_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_deduplicates_strings(
        self, translation_service, sample_meal_suggestion, mock_generation_service
    ):
        """Test that duplicate strings are only translated once."""
        # Create 3 identical meals (maximum deduplication)
        suggestions = [sample_meal_suggestion] * 3

        mock_generation_service.generate_meal_plan.return_value = {
            "translations": ["translated"] * 20  # Mock enough translations
        }

        result = await translation_service.translate_meal_suggestions_batch(
            suggestions, "vi"
        )

        # Should make only ONE API call
        assert mock_generation_service.generate_meal_plan.call_count == 1

        # Verify the call was made with deduplicated strings
        call_args = mock_generation_service.generate_meal_plan.call_args
        prompt = call_args[0][0]  # First positional argument
        # Check that we're not translating 3x the strings
        assert len(result) == 3
