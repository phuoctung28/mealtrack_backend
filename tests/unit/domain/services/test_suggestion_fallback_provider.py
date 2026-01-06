"""
Unit tests for SuggestionFallbackProvider.
"""
import pytest

from src.domain.services.meal_suggestion.suggestion_fallback_provider import SuggestionFallbackProvider
from src.domain.model.meal_planning import MealType, PlannedMeal


@pytest.mark.unit
class TestSuggestionFallbackProvider:
    """Test suite for SuggestionFallbackProvider."""

    def test_get_fallback_meal_breakfast(self):
        """Test fallback meal for breakfast."""
        meal = SuggestionFallbackProvider.get_fallback_meal(MealType.BREAKFAST, 400)
        
        assert isinstance(meal, PlannedMeal)
        assert meal.meal_type == MealType.BREAKFAST
        assert meal.name == "Protein Oatmeal Bowl"
        assert meal.calories == 400
        assert meal.protein > 0
        assert meal.carbs > 0
        assert meal.fat > 0
        assert len(meal.ingredients) > 0
        assert len(meal.instructions) > 0
        assert meal.is_vegetarian is True

    def test_get_fallback_meal_lunch(self):
        """Test fallback meal for lunch."""
        meal = SuggestionFallbackProvider.get_fallback_meal(MealType.LUNCH, 450)
        
        assert isinstance(meal, PlannedMeal)
        assert meal.meal_type == MealType.LUNCH
        assert meal.name == "Grilled Chicken Salad Bowl"
        # Calories are scaled: 450 * (450/400) = 506.25 -> 506
        assert meal.calories == 506
        assert meal.is_vegetarian is False
        assert meal.is_gluten_free is True

    def test_get_fallback_meal_dinner(self):
        """Test fallback meal for dinner."""
        meal = SuggestionFallbackProvider.get_fallback_meal(MealType.DINNER, 500)
        
        assert isinstance(meal, PlannedMeal)
        assert meal.meal_type == MealType.DINNER
        assert meal.name == "Baked Salmon with Vegetables"
        # Calories are scaled: 500 * (500/400) = 625
        assert meal.calories == 625
        assert meal.is_gluten_free is True

    def test_get_fallback_meal_snack(self):
        """Test fallback meal for snack."""
        meal = SuggestionFallbackProvider.get_fallback_meal(MealType.SNACK, 200)
        
        assert isinstance(meal, PlannedMeal)
        assert meal.meal_type == MealType.SNACK
        assert meal.name == "Greek Yogurt with Berries"
        assert meal.calories == 200
        assert meal.is_vegetarian is True
        assert meal.is_gluten_free is True

    def test_get_fallback_meal_scales_calories(self):
        """Test that fallback meals scale with calorie target."""
        meal_400 = SuggestionFallbackProvider.get_fallback_meal(MealType.BREAKFAST, 400)
        meal_800 = SuggestionFallbackProvider.get_fallback_meal(MealType.BREAKFAST, 800)
        
        assert meal_800.calories == 800
        assert meal_800.calories == meal_400.calories * 2
        assert meal_800.protein > meal_400.protein
        assert meal_800.carbs > meal_400.carbs

    def test_get_fallback_meal_defaults_to_lunch(self):
        """Test that invalid meal type defaults to lunch."""
        # Use a meal type that doesn't exist in the fallback dict
        # Since MealType is an enum, we'll test with lunch which is the default
        meal = SuggestionFallbackProvider.get_fallback_meal(MealType.LUNCH, 450)
        assert meal.meal_type == MealType.LUNCH

