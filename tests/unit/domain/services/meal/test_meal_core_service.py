"""
Unit tests for MealCoreService.
Tests meal operations and meal type determination.
"""
from datetime import datetime
from unittest.mock import Mock

import pytest

from src.domain.model.meal_planning import MealType
from src.domain.services.meal.meal_core_service import MealCoreService


@pytest.fixture
def service():
    """Create MealCoreService instance."""
    return MealCoreService()


class TestMealTypeDetermination:
    """Test meal type determination from time."""

    @pytest.mark.parametrize("hour,minute,expected", [
        (6, 0, MealType.BREAKFAST),
        (8, 30, MealType.BREAKFAST),
        (10, 0, MealType.BREAKFAST),
        (12, 0, MealType.LUNCH),
        (13, 30, MealType.LUNCH),
        (18, 0, MealType.DINNER),
        (20, 0, MealType.DINNER),
        (22, 0, MealType.SNACK),
        (3, 0, MealType.SNACK),
    ])
    def test_determine_meal_type(self, service, hour, minute, expected):
        """Meal type should be correctly determined from time."""
        meal_time = datetime(2024, 1, 15, hour, minute)
        result = service.determine_meal_type(meal_time)
        assert result == expected

    def test_determine_meal_type_defaults_to_now(self, service):
        """Without time argument, should use current time."""
        result = service.determine_meal_type()
        assert isinstance(result, MealType)


class TestCalorieTargets:
    """Test calorie target calculation."""

    def test_get_calorie_target_for_meal(self, service):
        """Should calculate correct calorie target."""
        daily = 2000
        
        breakfast = service.get_calorie_target_for_meal(MealType.BREAKFAST, daily)
        lunch = service.get_calorie_target_for_meal(MealType.LUNCH, daily)
        dinner = service.get_calorie_target_for_meal(MealType.DINNER, daily)
        
        assert breakfast == 500  # 25%
        assert lunch == 700      # 35%
        assert dinner == 600     # 30%

    def test_get_calorie_target_custom_distribution(self, service):
        """Should use custom distribution when provided."""
        daily = 2000
        custom = {MealType.BREAKFAST: 0.40}  # 40% for breakfast
        
        result = service.get_calorie_target_for_meal(
            MealType.BREAKFAST, daily, custom
        )
        assert result == 800


class TestNutritionCalculation:
    """Test nutrition calculation from food items."""

    def test_calculate_nutrition_aggregates_items(self, service):
        """Should sum nutrition from all items."""
        from src.domain.model.nutrition import Macros
        
        items = [
            Mock(calories=200, macros=Macros(protein=15, carbs=20, fat=8)),
            Mock(calories=300, macros=Macros(protein=25, carbs=30, fat=12)),
        ]
        
        result = service.calculate_nutrition(items)
        
        assert result.calories == 500
        assert result.macros.protein == 40
        assert result.macros.carbs == 50
        assert result.macros.fat == 20

    def test_calculate_nutrition_handles_missing_values(self, service):
        """Should handle items with zero nutrition values."""
        from src.domain.model.nutrition import Macros
        
        items = [
            Mock(calories=100, macros=Macros(protein=0, carbs=10, fat=5)),
        ]
        
        result = service.calculate_nutrition(items)
        
        assert result.calories == 100
        assert result.macros.protein == 0
        assert result.macros.carbs == 10


class TestMealValidation:
    """Test meal validation."""

    def test_validate_meal_requires_name(self, service):
        """Meal without name should fail validation."""
        meal = Mock(spec=['name', 'food_items', 'nutrition'])
        meal.name = ""  # Empty name
        meal.food_items = [Mock()]
        meal.nutrition = None
        errors = service.validate_meal(meal)
        assert "Meal name is required" in errors

    def test_validate_meal_requires_items(self, service):
        """Meal without items should fail validation."""
        meal = Mock(name="Test", food_items=[], nutrition=None)
        errors = service.validate_meal(meal)
        assert "Meal must have at least one food item" in errors

    def test_validate_meal_valid_returns_empty(self, service):
        """Valid meal should return empty error list."""
        from src.domain.model.nutrition import Macros
        
        meal = Mock(
            name="Test Meal",
            food_items=[Mock()],
            nutrition=Mock(calories=100, macros=Macros(protein=10, carbs=20, fat=5))
        )
        errors = service.validate_meal(meal)
        assert len(errors) == 0
