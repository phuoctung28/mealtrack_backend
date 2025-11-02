"""
Unit tests for MealMapper.
"""
import pytest
from datetime import datetime

from src.api.mappers.meal_mapper import MealMapper, STATUS_MAPPING
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.nutrition import Nutrition, FoodItem, Macros


class TestMealMapper:
    """Test suite for MealMapper."""

    def test_to_simple_response(self):
        """Test converting Meal to SimpleMealResponse."""
        meal = Meal(
            meal_id="meal-123",
            user_id="user-456",
            status=MealStatus.READY,
            dish_name="Chicken Bowl",
            ready_at=datetime(2025, 1, 15, 12, 30),
            created_at=datetime(2025, 1, 15, 12, 0),
            error_message=None
        )
        
        result = MealMapper.to_simple_response(meal)
        
        assert result.meal_id == "meal-123"
        assert result.status == "ready"
        assert result.dish_name == "Chicken Bowl"
        assert result.ready_at == datetime(2025, 1, 15, 12, 30)
        assert result.error_message is None
        assert result.created_at == datetime(2025, 1, 15, 12, 0)

    def test_to_simple_response_with_error(self):
        """Test converting failed meal to SimpleMealResponse."""
        meal = Meal(
            meal_id="meal-failed",
            user_id="user-789",
            status=MealStatus.FAILED,
            dish_name="Failed Meal",
            ready_at=None,
            created_at=datetime(2025, 1, 15, 13, 0),
            error_message="Analysis failed"
        )
        
        result = MealMapper.to_simple_response(meal)
        
        assert result.status == "failed"
        assert result.error_message == "Analysis failed"

    def test_status_mapping(self):
        """Test status mapping from domain to API."""
        assert STATUS_MAPPING["PROCESSING"] == "pending"
        assert STATUS_MAPPING["ANALYZING"] == "analyzing"
        assert STATUS_MAPPING["ENRICHING"] == "analyzing"
        assert STATUS_MAPPING["READY"] == "ready"
        assert STATUS_MAPPING["FAILED"] == "failed"

    def test_to_detailed_response_with_nutrition(self):
        """Test converting Meal with nutrition to DetailedMealResponse."""
        food_items = [
            FoodItem(
                id="item-1",
                name="Chicken Breast",
                quantity=200,
                unit="g",
                calories=220,
                macros=Macros(protein=40, carbs=0, fat=5),
                confidence=0.95,
                fdc_id=123456,
                is_custom=False
            ),
            FoodItem(
                id="item-2",
                name="Rice",
                quantity=150,
                unit="g",
                calories=195,
                macros=Macros(protein=4, carbs=43, fat=0.4),
                confidence=0.90,
                fdc_id=789012,
                is_custom=False
            )
        ]
        
        nutrition = Nutrition(
            calories=415,
            macros=Macros(protein=44, carbs=43, fat=5.4),
            food_items=food_items
        )
        
        meal = Meal(
            meal_id="meal-detailed",
            user_id="user-123",
            status=MealStatus.READY,
            dish_name="Chicken and Rice",
            ready_at=datetime(2025, 1, 15, 14, 0),
            created_at=datetime(2025, 1, 15, 13, 30),
            nutrition=nutrition,
            weight_grams=350
        )
        
        result = MealMapper.to_detailed_response(meal, image_url="https://example.com/image.jpg")
        
        assert result.meal_id == "meal-detailed"
        assert result.dish_name == "Chicken and Rice"
        assert result.total_calories == 415
        assert result.total_nutrition.protein == 44
        assert result.total_nutrition.carbs == 43
        assert result.total_nutrition.fat == 5.4
        assert len(result.food_items) == 2
        assert result.food_items[0].name == "Chicken Breast"
        assert result.food_items[0].fdc_id == 123456
        assert result.food_items[1].name == "Rice"
        assert result.image_url == "https://example.com/image.jpg"
        assert result.total_weight_grams == 350

    def test_to_detailed_response_with_custom_food_item(self):
        """Test detailed response with custom food item."""
        food_items = [
            FoodItem(
                id="item-custom",
                name="Homemade Sauce",
                quantity=50,
                unit="g",
                calories=60,
                macros=Macros(protein=1, carbs=8, fat=2),
                confidence=1.0,
                fdc_id=None,
                is_custom=True
            )
        ]
        
        nutrition = Nutrition(
            calories=60,
            macros=Macros(protein=1, carbs=8, fat=2),
            food_items=food_items
        )
        
        meal = Meal(
            meal_id="meal-custom",
            user_id="user-456",
            status=MealStatus.READY,
            dish_name="Custom Meal",
            ready_at=datetime(2025, 1, 15, 15, 0),
            created_at=datetime(2025, 1, 15, 14, 30),
            nutrition=nutrition
        )
        
        result = MealMapper.to_detailed_response(meal)
        
        assert len(result.food_items) == 1
        assert result.food_items[0].is_custom is True
        assert result.food_items[0].fdc_id is None
        assert result.food_items[0].custom_nutrition is not None
        assert result.food_items[0].custom_nutrition.calories_per_100g == 120.0  # 60 * (100/50)

    def test_to_detailed_response_without_nutrition(self):
        """Test detailed response when nutrition is None."""
        meal = Meal(
            meal_id="meal-no-nutrition",
            user_id="user-789",
            status=MealStatus.PROCESSING,
            dish_name="Processing Meal",
            ready_at=None,
            created_at=datetime(2025, 1, 15, 16, 0),
            nutrition=None
        )
        
        result = MealMapper.to_detailed_response(meal)
        
        assert result.total_calories == 0
        assert result.food_items == []
        assert result.total_nutrition is None

    def test_to_meal_list_response(self):
        """Test converting list of meals to MealListResponse."""
        meals = [
            Meal(
                meal_id="meal-1",
                user_id="user-123",
                status=MealStatus.READY,
                dish_name="Meal 1",
                ready_at=datetime(2025, 1, 15, 12, 0),
                created_at=datetime(2025, 1, 15, 11, 30),
                nutrition=Nutrition(
                    calories=400,
                    macros=Macros(protein=30, carbs=40, fat=10),
                    food_items=[
                        FoodItem(
                            id="item-1",
                            name="Item 1",
                            quantity=100,
                            unit="g",
                            calories=400,
                            macros=Macros(protein=30, carbs=40, fat=10),
                            confidence=0.9
                        )
                    ]
                )
            ),
            Meal(
                meal_id="meal-2",
                user_id="user-123",
                status=MealStatus.PROCESSING,
                dish_name="Meal 2",
                ready_at=None,
                created_at=datetime(2025, 1, 15, 13, 0),
                nutrition=None
            )
        ]
        
        result = MealMapper.to_meal_list_response(
            meals=meals,
            total=10,
            page=1,
            page_size=2,
            image_urls={"meal-1": "https://example.com/meal1.jpg"}
        )
        
        assert result.total == 10
        assert result.page == 1
        assert result.page_size == 2
        assert result.total_pages == 5
        assert len(result.meals) == 2

    def test_map_nutrition_from_dict(self):
        """Test creating Nutrition from dictionary."""
        nutrition_dict = {
            "nutrition_id": "nutr-123",
            "calories": 500,
            "protein_g": 35,
            "carbs_g": 55,
            "fat_g": 15,
            "sugar_g": 10,
            "sodium_mg": 400
        }
        
        result = MealMapper.map_nutrition_from_dict(nutrition_dict)
        
        assert result.nutrition_id == "nutr-123"
        assert result.calories == 500
        assert result.protein_g == 35
        assert result.carbs_g == 55
        assert result.fat_g == 15
        assert result.sugar_g == 10
        assert result.sodium_mg == 400

    def test_map_food_item_from_dict(self):
        """Test creating FoodItem from dictionary."""
        item_dict = {
            "id": "item-456",
            "name": "Salmon",
            "category": "protein",
            "quantity": 180,
            "unit": "g",
            "description": "Fresh salmon fillet",
            "nutrition": {
                "nutrition_id": "nutr-456",
                "calories": 350,
                "protein_g": 40,
                "carbs_g": 0,
                "fat_g": 20,
                "sugar_g": 0,
                "sodium_mg": 80
            }
        }
        
        result = MealMapper.map_food_item_from_dict(item_dict)
        
        assert result.id == "item-456"
        assert result.name == "Salmon"
        assert result.category == "protein"
        assert result.quantity == 180
        assert result.unit == "g"
        assert result.description == "Fresh salmon fillet"
        assert result.nutrition is not None
        assert result.nutrition.calories == 350

    def test_to_daily_nutrition_response(self):
        """Test converting daily macros data to DailyNutritionResponse."""
        daily_macros_data = {
            "date": "2025-01-15",
            "user_id": "user-123",
            "target_calories": 2000.0,
            "target_macros": {
                "protein": 150.0,
                "carbs": 250.0,
                "fat": 67.0
            },
            "total_calories": 1500.0,
            "total_protein": 100.0,
            "total_carbs": 180.0,
            "total_fat": 50.0
        }
        
        result = MealMapper.to_daily_nutrition_response(daily_macros_data)
        
        assert result.date == "2025-01-15"
        assert result.target_calories == 2000.0
        assert result.target_macros.protein == 150.0
        assert result.consumed_calories == 1500.0
        assert result.consumed_macros.protein == 100.0
        assert result.remaining_calories == 500.0
        assert result.remaining_macros.protein == 50.0
        assert result.completion_percentage["calories"] == 75.0
        assert result.completion_percentage["protein"] == pytest.approx(66.67, rel=0.01)

    def test_to_daily_nutrition_response_missing_target_calories(self):
        """Test error when target_calories is missing."""
        daily_macros_data = {
            "target_macros": {"protein": 150, "carbs": 250, "fat": 67}
        }
        
        with pytest.raises(Exception, match="User profile not found"):
            MealMapper.to_daily_nutrition_response(daily_macros_data)

    def test_to_daily_nutrition_response_over_target(self):
        """Test when consumed calories exceed target."""
        daily_macros_data = {
            "date": "2025-01-16",
            "user_id": "user-456",
            "target_calories": 2000.0,
            "target_macros": {
                "protein": 150.0,
                "carbs": 250.0,
                "fat": 67.0
            },
            "total_calories": 2500.0,
            "total_protein": 180.0,
            "total_carbs": 300.0,
            "total_fat": 80.0
        }
        
        result = MealMapper.to_daily_nutrition_response(daily_macros_data)
        
        assert result.remaining_calories == 0  # Should not be negative
        assert result.remaining_macros.protein == 0
        assert result.completion_percentage["calories"] == 125.0

    def test_to_detailed_response_with_legacy_nutrition_structure(self):
        """Test detailed response with legacy nutrition structure (direct properties)."""
        # Create nutrition with direct protein/carbs/fat properties
        nutrition = Nutrition(
            calories=400,
            macros=Macros(protein=30, carbs=45, fat=12),
            food_items=[]
        )
        
        meal = Meal(
            meal_id="meal-legacy",
            user_id="user-999",
            status=MealStatus.READY,
            dish_name="Legacy Meal",
            ready_at=datetime(2025, 1, 15, 17, 0),
            created_at=datetime(2025, 1, 15, 16, 30),
            nutrition=nutrition
        )
        
        result = MealMapper.to_detailed_response(meal)
        
        assert result.total_nutrition is not None
        assert result.total_nutrition.protein == 30
        assert result.total_nutrition.carbs == 45
        assert result.total_nutrition.fat == 12

