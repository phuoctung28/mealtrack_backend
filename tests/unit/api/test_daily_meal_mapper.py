"""
Unit tests for DailyMealMapper.
"""
import pytest

from src.api.mappers.daily_meal_mapper import DailyMealMapper
from src.api.schemas.request import UserPreferencesRequest
from src.domain.model import SimpleMacroTargets, PlannedMeal, MealType


class TestDailyMealMapper:
    """Test suite for DailyMealMapper."""

    def test_map_user_preferences_to_dict(self):
        """Test mapping UserPreferencesRequest to dictionary."""
        request = UserPreferencesRequest(
            age=30,
            gender="male",
            height=175,
            weight=75,
            activity_level="moderately_active",
            goal="maintain_weight",
            dietary_preferences=["vegan", "gluten_free"],
            health_conditions=["diabetes"],
            target_calories=2000,
            target_protein=150,
            target_carbs=250,
            target_fat=67
        )
        
        result = DailyMealMapper.map_user_preferences_to_dict(request)
        
        assert result["age"] == 30
        assert result["gender"] == "male"
        assert result["height"] == 175
        assert result["weight"] == 75
        assert result["activity_level"] == "moderately_active"
        assert result["goal"] == "maintain_weight"
        assert result["dietary_preferences"] == ["vegan", "gluten_free"]
        assert result["health_conditions"] == ["diabetes"]
        assert result["target_calories"] == 2000
        assert result["target_macros"]["protein"] == 150
        assert result["target_macros"]["carbs"] == 250
        assert result["target_macros"]["fat"] == 67

    def test_map_user_preferences_with_none_lists(self):
        """Test mapping when lists are None."""
        request = UserPreferencesRequest(
            age=25,
            gender="female",
            height=165,
            weight=60,
            activity_level="lightly_active",
            goal="lose_weight",
            dietary_preferences=None,
            health_conditions=None,
            target_calories=1800,
            target_protein=120,
            target_carbs=180,
            target_fat=60
        )
        
        result = DailyMealMapper.map_user_preferences_to_dict(request)
        
        assert result["dietary_preferences"] == []
        assert result["health_conditions"] == []

    def test_map_planned_meal_to_schema(self):
        """Test mapping PlannedMeal to SuggestedMealResponse."""
        meal = PlannedMeal(
            meal_type=MealType.BREAKFAST,
            name="Oatmeal Bowl",
            description="Healthy breakfast",
            calories=400,
            protein=20.0,
            carbs=60.0,
            fat=10.0,
            prep_time=5,
            cook_time=10,
            ingredients=["100g oats", "1 banana", "15ml honey"],
            instructions=["Cook oats", "Add toppings"],
            is_vegetarian=True,
            is_vegan=False,
            is_gluten_free=True
        )
        # Set extra attributes for mapper
        meal.id = "meal-123"
        meal.preparation_time = {"prep": 5, "cook": 10, "total": 15}
        meal.tags = ["vegetarian", "gluten-free", "italian"]
        
        result = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        assert result.meal_id == "meal-123"
        assert result.meal_type == "breakfast"
        assert result.name == "Oatmeal Bowl"
        assert result.description == "Healthy breakfast"
        assert result.prep_time == 5
        assert result.cook_time == 10
        assert result.total_time == 15
        assert result.calories == 400
        assert result.protein == 20.0
        assert result.carbs == 60.0
        assert result.fat == 10.0
        assert result.ingredients == ["100g oats", "1 banana", "15ml honey"]
        assert result.instructions == ["Cook oats", "Add toppings"]
        assert result.is_vegetarian is True
        assert result.is_vegan is False
        assert result.is_gluten_free is True
        assert result.cuisine_type == "italian"

    def test_map_planned_meal_with_vegan_tag(self):
        """Test mapping meal with vegan tag."""
        meal = PlannedMeal(
            meal_type=MealType.LUNCH,
            name="Vegan Bowl",
            description="Plant-based lunch",
            calories=500,
            protein=25.0,
            carbs=70.0,
            fat=15.0,
            prep_time=10,
            cook_time=20,
            ingredients=["200g quinoa", "150g chickpeas"],
            instructions=["Mix all"],
            is_vegetarian=True,
            is_vegan=True,
            is_gluten_free=False
        )
        # Set extra attributes for mapper
        meal.id = "meal-456"
        meal.preparation_time = {"prep": 10, "cook": 20, "total": 30}
        meal.tags = ["vegan", "vegetarian"]
        
        result = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        assert result.is_vegan is True
        assert result.is_vegetarian is True

    def test_map_planned_meal_without_preparation_time(self):
        """Test mapping meal without preparation time."""
        meal = PlannedMeal(
            meal_type=MealType.DINNER,
            name="Quick Meal",
            description="Fast dinner",
            calories=600,
            protein=35.0,
            carbs=50.0,
            fat=25.0,
            prep_time=0,
            cook_time=0,
            ingredients=["300g chicken"],
            instructions=["Grill"],
            is_vegetarian=False,
            is_vegan=False,
            is_gluten_free=False
        )
        # Set extra attributes for mapper
        meal.id = "meal-789"
        meal.preparation_time = None
        meal.tags = []
        
        result = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        assert result.prep_time == 0
        assert result.cook_time == 0
        assert result.total_time == 0

    def test_map_handler_response_to_dto(self):
        """Test mapping handler response to DailyMealSuggestionsResponse."""
        handler_response = {
            "date": "2025-01-15",
            "meal_count": 3,
            "meals": [
                {
                    "meal_id": "m1",
                    "meal_type": "breakfast",
                    "name": "Oatmeal",
                    "description": "Healthy",
                    "calories": 400,
                    "protein": 20.0,
                    "carbs": 60.0,
                    "fat": 10.0,
                    "ingredients": ["oats"],
                    "instructions": ["cook"],
                    "prep_time": 5,
                    "cook_time": 10,
                    "total_time": 15,
                    "is_vegetarian": True,
                    "is_vegan": False,
                    "is_gluten_free": True,
                    "cuisine_type": "International"
                }
            ],
            "daily_totals": {
                "calories": 400,
                "protein": 20.0,
                "carbs": 60.0,
                "fat": 10.0
            }
        }
        
        target_calories = 2000.0
        target_macros = SimpleMacroTargets(protein=150.0, carbs=250.0, fat=67.0)
        
        result = DailyMealMapper.map_handler_response_to_dto(
            handler_response,
            target_calories,
            target_macros
        )
        
        assert result.date == "2025-01-15"
        assert result.meal_count == 3
        assert len(result.meals) == 1
        assert result.meals[0].name == "Oatmeal"
        assert result.daily_totals.calories == 400
        assert result.target_totals.calories == 2000
        assert result.target_totals.protein == 150.0

    def test_map_to_suggestions_response_with_dict_macros(self):
        """Test mapping with dict macros."""
        result_data = {
            "date": "2025-01-16",
            "meal_count": 2,
            "meals": [
                {
                    "meal_id": "m2",
                    "meal_type": "lunch",
                    "name": "Salad",
                    "description": "Fresh",
                    "calories": 500,
                    "protein": 25.0,
                    "carbs": 45.0,
                    "fat": 20.0,
                    "ingredients": ["lettuce"],
                    "instructions": ["toss"],
                    "prep_time": 10,
                    "cook_time": 0,
                    "total_time": 10,
                    "is_vegetarian": True,
                    "is_vegan": True,
                    "is_gluten_free": True,
                    "cuisine_type": "Mediterranean"
                }
            ],
            "daily_totals": {
                "calories": 500,
                "protein": 25.0,
                "carbs": 45.0,
                "fat": 20.0
            },
            "target_calories": 2000.0,
            "target_macros": {
                "protein": 150.0,
                "carbs": 250.0,
                "fat": 67.0
            }
        }
        
        result = DailyMealMapper.map_to_suggestions_response(result_data)
        
        assert result.date == "2025-01-16"
        assert result.target_totals.protein == 150.0

    def test_map_to_suggestions_response_missing_target_calories(self):
        """Test error when target_calories is missing."""
        result_data = {
            "meals": [],
            "target_macros": {"protein": 150.0, "carbs": 250.0, "fat": 67.0}
        }
        
        with pytest.raises(ValueError, match="target_calories is required"):
            DailyMealMapper.map_to_suggestions_response(result_data)

    def test_map_to_suggestions_response_missing_target_macros(self):
        """Test error when target_macros is missing."""
        result_data = {
            "meals": [],
            "target_calories": 2000.0
        }
        
        with pytest.raises(ValueError, match="target_macros is required"):
            DailyMealMapper.map_to_suggestions_response(result_data)

    def test_map_to_single_meal_response(self):
        """Test mapping single meal response."""
        result_data = {
            "meal": {
                "name": "Dinner",
                "calories": 600
            }
        }
        
        result = DailyMealMapper.map_to_single_meal_response(result_data)
        
        assert "meal" in result
        assert result["meal"]["name"] == "Dinner"
        assert result["meal"]["calories"] == 600

    def test_map_to_single_meal_response_empty(self):
        """Test mapping single meal response when meal is missing."""
        result_data = {}
        
        result = DailyMealMapper.map_to_single_meal_response(result_data)
        
        assert result["meal"] == {}

    def test_map_planned_meal_with_empty_tags(self):
        """Test mapping meal with empty tags list."""
        meal = PlannedMeal(
            meal_type=MealType.SNACK,
            name="Simple Snack",
            description="Quick snack",
            calories=150,
            protein=5.0,
            carbs=20.0,
            fat=5.0,
            prep_time=0,
            cook_time=0,
            ingredients=["apple"],
            instructions=["eat"],
            is_vegetarian=False,
            is_vegan=False,
            is_gluten_free=False
        )
        # Set extra attributes for mapper
        meal.id = "meal-empty"
        meal.preparation_time = {"prep": 0, "cook": 0, "total": 0}
        meal.tags = []
        
        result = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        assert result.is_vegetarian is False
        assert result.is_vegan is False
        assert result.is_gluten_free is False
        assert result.cuisine_type is None

    def test_map_planned_meal_with_minimal_instructions(self):
        """Test mapping meal with minimal instructions."""
        meal = PlannedMeal(
            meal_type=MealType.BREAKFAST,
            name="Simple Meal",
            description="Test",
            calories=300,
            protein=15.0,
            carbs=40.0,
            fat=8.0,
            prep_time=5,
            cook_time=5,
            ingredients=["ingredient1"],
            instructions=["Prepare and serve"],
            is_vegetarian=False,
            is_vegan=False,
            is_gluten_free=False
        )
        # Set extra attributes for mapper
        meal.id = "meal-simple"
        meal.preparation_time = {"prep": 5, "cook": 5, "total": 10}
        meal.tags = []
        
        result = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        assert result.instructions == ["Prepare and serve"]

