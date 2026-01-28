"""
Unit tests for meal analysis translation service.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from src.domain.model.meal import Meal, MealStatus, MealTranslation, FoodItemTranslation
from src.domain.model.meal import MealImage
from src.domain.model.nutrition import FoodItem, Macros
from src.domain.services.meal_analysis.translation_service import MealAnalysisTranslationService


class TestMealAnalysisTranslationService:
    """Tests for MealAnalysisTranslationService."""

    @pytest.fixture
    def mock_translation_repo(self):
        """Create a mock translation repository."""
        return Mock()

    @pytest.fixture
    def mock_translation_service(self):
        """Create a mock translation service."""
        return Mock()

    @pytest.fixture
    def translation_service(self, mock_translation_repo, mock_translation_service):
        """Create a MealAnalysisTranslationService with mocked dependencies."""
        return MealAnalysisTranslationService(
            translation_repo=mock_translation_repo,
            translation_service=mock_translation_service
        )

    @pytest.fixture
    def sample_meal(self):
        """Create a sample meal for testing (PROCESSING status to avoid validation)."""
        return Meal(
            meal_id=str(uuid4()),
            user_id=str(uuid4()),
            status=MealStatus.PROCESSING,
            created_at=datetime.utcnow(),
            image=MealImage(
                image_id=str(uuid4()),
                format="jpeg",
                size_bytes=1024,
                url="https://example.com/image.jpg"
            )
        )

    @pytest.fixture
    def sample_food_items(self):
        """Create sample food items for testing."""
        return [
            FoodItem(
                id=str(uuid4()),
                name="Chicken breast",
                quantity=150,
                unit="g",
                calories=165,
                macros=Macros(protein=31, carbs=0, fat=3.6)
            ),
            FoodItem(
                id=str(uuid4()),
                name="Brown rice",
                quantity=200,
                unit="g",
                calories=220,
                macros=Macros(protein=5, carbs=46, fat=1.8)
            ),
        ]

    @pytest.mark.asyncio
    async def test_translate_meal_skips_english(self, translation_service, sample_meal, sample_food_items):
        """Test that English translation is skipped."""
        result = await translation_service.translate_meal(
            meal=sample_meal,
            dish_name="Grilled chicken",
            food_items=sample_food_items,
            target_language="en"
        )

        assert result is None
        translation_service._translator._batch_translate.assert_not_called()

    @pytest.mark.asyncio
    async def test_translate_meal_skips_empty_food_items(self, translation_service, sample_meal):
        """Test that translation is skipped when there are no food items."""
        result = await translation_service.translate_meal(
            meal=sample_meal,
            dish_name="Grilled chicken",
            food_items=[],
            target_language="vi"
        )

        assert result is None

    def test_extract_translatable_strings(self, translation_service, sample_food_items):
        """Test extraction of strings for translation."""
        dish_name = "Grilled chicken with rice"
        food_items = sample_food_items

        strings, paths = translation_service._extract_translatable_strings(dish_name, food_items)

        # dish_name + 2 food item names (FoodItem doesn't have description)
        assert len(strings) == 3
        assert strings[0] == "Grilled chicken with rice"
        assert "dish_name" in paths

    def test_build_translation(self, translation_service):
        """Test building a translation domain model."""
        item_id = str(uuid4())
        meal_id = "test-meal-123"
        dish_name = "Grilled chicken"
        food_items = [
            FoodItem(
                id=item_id,
                name="Chicken breast",
                quantity=150,
                unit="g",
                calories=165,
                macros=Macros(protein=31, carbs=0, fat=3.6)
            ),
        ]

        # Only dish_name and food item name (no description since FoodItem doesn't have it)
        translated_strings = ["Gà nướng", "Ức gà"]
        paths = ["dish_name", "food_items[0].name"]
        language = "vi"

        result = translation_service._build_translation(
            meal_id=meal_id,
            dish_name=dish_name,
            food_items=food_items,
            translated_strings=translated_strings,
            paths=paths,
            language=language
        )

        assert result.meal_id == meal_id
        assert result.language == language
        assert result.dish_name == "Gà nướng"
        assert len(result.food_items) == 1
        assert result.food_items[0].name == "Ức gà"
        assert result.food_items[0].food_item_id == item_id

    @pytest.mark.asyncio
    async def test_translate_with_retry_success(self, translation_service):
        """Test successful translation with retry logic."""
        strings = ["Chicken", "Rice"]
        language = "vi"

        # First call succeeds
        translation_service._translator._batch_translate = AsyncMock(
            return_value=["Gà", "Cơm"]
        )

        results = await translation_service._translate_with_retry(strings, language)

        assert results == ["Gà", "Cơm"]
        translation_service._translator._batch_translate.assert_called_once()

    @pytest.mark.asyncio
    async def test_translate_with_retry_fallback(self, translation_service):
        """Test translation fallback to original on failure."""
        strings = ["Chicken", "Rice"]
        language = "vi"

        # First call partially fails
        translation_service._translator._batch_translate = AsyncMock(
            side_effect=[
                ["Gà", ""],  # Second item failed
                ["Cơm"]  # Retry succeeds
            ]
        )

        results = await translation_service._translate_with_retry(strings, language)

        assert results == ["Gà", "Cơm"]
        assert translation_service._translator._batch_translate.call_count == 2
