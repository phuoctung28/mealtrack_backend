"""
Unit tests for DailyMealMapper.
"""
import pytest

from src.api.mappers.daily_meal_mapper import DailyMealMapper
from src.api.schemas.request import UserPreferencesRequest
from src.api.schemas.response import MacroTargetsResponse
from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.model.meal_plan import PlannedMeal, MealType


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
            goal="maintenance",
            dietary_preferences=["vegan", "gluten_free"],
            health_conditions=["diabetes"],
            target_calories=2000,
            target_macros=MacroTargetsResponse(protein=150, carbs=250, fat=67)
        )
        
        result = DailyMealMapper.map_user_preferences_to_dict(request)
        
        assert result["age"] == 30
        assert result["gender"] == "male"
        assert result["height"] == 175
        assert result["weight"] == 75
        assert result["activity_level"] == "moderately_active"
        assert result["goal"] == "maintenance"
        assert result["dietary_preferences"] == ["vegan", "gluten_free"]
        assert result["health_conditions"] == ["diabetes"]
        assert result["target_calories"] == 2000
        assert result["target_macros"] == request.target_macros

    def test_map_user_preferences_with_none_lists(self):
        """Test mapping when lists are None."""
        request = UserPreferencesRequest(
            age=25,
            gender="female",
            height=165,
            weight=60,
            activity_level="lightly_active",
            goal="cutting",
            dietary_preferences=None,
            health_conditions=None,
            target_calories=1800,
            target_macros=MacroTargetsResponse(protein=120, carbs=180, fat=60)
        )
        
        result = DailyMealMapper.map_user_preferences_to_dict(request)
        
        assert result["dietary_preferences"] == []
        assert result["health_conditions"] == []

    def test_map_planned_meal_to_schema(self):
        """Test mapping PlannedMeal to SuggestedMealResponse."""
        meal = PlannedMeal(
            id="meal-123",
            meal_type=MealType.BREAKFAST,
            name="Oatmeal Bowl",
            description="Healthy breakfast",
            calories=400,
            protein=20.0,
            carbs=60.0,
            fat=10.0,
            ingredients=["100g oats", "1 banana", "15ml honey"],
            instructions=["Cook oats", "Add toppings"],
            preparation_time={"prep": 5, "cook": 10, "total": 15},
            tags=["vegetarian", "gluten-free", "italian"]
        )
        
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
            id="meal-456",
            meal_type=MealType.LUNCH,
            name="Vegan Bowl",
            description="Plant-based lunch",
            calories=500,
            protein=25.0,
            carbs=70.0,
            fat=15.0,
            ingredients=["200g quinoa", "150g chickpeas"],
            instructions=["Mix all"],
            preparation_time={"prep": 10, "cook": 20, "total": 30},
            tags=["vegan", "vegetarian"]
        )
        
        result = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        assert result.is_vegan is True
        assert result.is_vegetarian is True

    def test_map_planned_meal_without_preparation_time(self):
        """Test mapping meal without preparation time."""
        meal = PlannedMeal(
            id="meal-789",
            meal_type=MealType.DINNER,
            name="Quick Meal",
            description="Fast dinner",
            calories=600,
            protein=35.0,
            carbs=50.0,
            fat=25.0,
            ingredients=["300g chicken"],
            instructions=["Grill"],
            preparation_time=None,
            tags=[]
        )
        
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
        assert result.daily_totals["calories"] == 400
        assert result.target_totals["calories"] == 2000
        assert result.target_totals["protein"] == 150.0

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
        assert result.target_totals["protein"] == 150.0

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
            id="meal-empty",
            meal_type=MealType.SNACK,
            name="Simple Snack",
            description="Quick snack",
            calories=150,
            protein=5.0,
            carbs=20.0,
            fat=5.0,
            ingredients=["apple"],
            instructions=["eat"],
            preparation_time={"prep": 0, "cook": 0, "total": 0},
            tags=[]
        )
        
        result = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        assert result.is_vegetarian is False
        assert result.is_vegan is False
        assert result.is_gluten_free is False
        assert result.cuisine_type is None

    def test_map_planned_meal_without_instructions(self):
        """Test mapping meal without instructions."""
        meal = PlannedMeal(
            id="meal-no-inst",
            meal_type=MealType.BREAKFAST,
            name="No Instructions",
            description="Test",
            calories=300,
            protein=15.0,
            carbs=40.0,
            fat=8.0,
            ingredients=["ingredient1"],
            instructions=None,
            preparation_time={"prep": 5, "cook": 5, "total": 10},
            tags=[]
        )
        
        result = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        assert result.instructions == []

