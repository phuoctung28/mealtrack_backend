"""
Unit tests for meal edit domain model functionality.
"""
import pytest
import uuid
from datetime import datetime

from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.model.nutrition import Nutrition, FoodItem, Macros


@pytest.mark.unit
class TestMealEditDomain:
    """Test meal edit domain functionality."""
    
    def test_meal_mark_edited_updates_fields(self):
        """Test that mark_edited updates all edit tracking fields."""
        # Arrange
        original_meal = Meal(
            meal_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            status=MealStatus.READY,
            created_at=datetime.now(),
            image=MealImage(
                image_id=str(uuid.uuid4()),
                format="jpeg",
                size_bytes=100000,
                url="https://example.com/image.jpg"
            ),
            dish_name="Original Meal",
            nutrition=Nutrition(
                calories=500.0,
                macros=Macros(
                    protein=30.0,
                    carbs=50.0,
                    fat=20.0,
                ),
                food_items=[],
                confidence_score=0.9
            ),
            ready_at=datetime.now(),
            edit_count=0,
            is_manually_edited=False
        )
        
        new_nutrition = Nutrition(
            calories=600.0,
            macros=Macros(
                protein=35.0,
                carbs=55.0,
                fat=25.0,
            ),
            food_items=[],
            confidence_score=0.9
        )
        
        # Act
        edited_meal = original_meal.mark_edited(new_nutrition, "Updated Meal")
        
        # Assert
        assert edited_meal.dish_name == "Updated Meal"
        assert edited_meal.nutrition == new_nutrition
        assert edited_meal.edit_count == 1
        assert edited_meal.is_manually_edited is True
        assert edited_meal.last_edited_at is not None
        assert edited_meal.updated_at is not None
        assert edited_meal.status == MealStatus.READY
        
        # Original meal should be unchanged
        assert original_meal.edit_count == 0
        assert original_meal.is_manually_edited is False
    
    def test_meal_mark_edited_increments_count(self):
        """Test that mark_edited increments edit count."""
        # Arrange
        meal = Meal(
            meal_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            status=MealStatus.READY,
            created_at=datetime.now(),
            image=MealImage(
                image_id=str(uuid.uuid4()),
                format="jpeg",
                size_bytes=100000,
                url="https://example.com/image.jpg"
            ),
            nutrition=Nutrition(
                calories=400.0,
                macros=Macros(protein=25.0, carbs=40.0, fat=15.0),
                food_items=[],
                confidence_score=0.9
            ),
            ready_at=datetime.now(),
            edit_count=2,  # Already edited twice
            is_manually_edited=True
        )
        
        nutrition = Nutrition(
            calories=500.0,
            macros=Macros(protein=30.0, carbs=50.0, fat=20.0),
            food_items=[],
            confidence_score=0.9
        )
        
        # Act
        edited_meal = meal.mark_edited(nutrition, "Test Meal")
        
        # Assert
        assert edited_meal.edit_count == 3
        assert edited_meal.is_manually_edited is True
    
    def test_meal_preserves_other_fields_when_edited(self):
        """Test that mark_edited preserves other meal fields."""
        # Arrange
        original_created_at = datetime.now()
        original_ready_at = datetime.now()
        
        meal = Meal(
            meal_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            status=MealStatus.READY,
            created_at=original_created_at,
            image=MealImage(
                image_id=str(uuid.uuid4()),
                format="jpeg",
                size_bytes=100000,
                url="https://example.com/image.jpg"
            ),
            nutrition=Nutrition(
                calories=400.0,
                macros=Macros(protein=25.0, carbs=40.0, fat=15.0),
                food_items=[],
                confidence_score=0.9
            ),
            ready_at=original_ready_at,
            error_message="Some error",
            raw_gpt_json='{"test": "data"}'
        )
        
        nutrition = Nutrition(
            calories=500.0,
            macros=Macros(protein=30.0, carbs=50.0, fat=20.0),
            food_items=[],
            confidence_score=0.9
        )
        
        # Act
        edited_meal = meal.mark_edited(nutrition, "Test Meal")
        
        # Assert
        assert edited_meal.meal_id == meal.meal_id
        assert edited_meal.user_id == meal.user_id
        assert edited_meal.created_at == original_created_at
        assert edited_meal.ready_at == original_ready_at
        assert edited_meal.error_message == "Some error"
        assert edited_meal.raw_gpt_json == '{"test": "data"}'
        assert edited_meal.image.image_id == meal.image.image_id


@pytest.mark.unit
class TestFoodItemEditSupport:
    """Test food item edit support functionality."""
    
    def test_food_item_with_edit_fields(self):
        """Test food item with edit support fields."""
        # Arrange & Act
        food_item = FoodItem(
            name="Grilled Chicken",
            quantity=150.0,
            unit="g",
            calories=248.0,
            macros=Macros(
                protein=46.2,
                carbs=0.0,
                fat=5.4,
            ),
            food_item_id="test-food-item-id",
            fdc_id=171077,
            is_custom=False
        )
        
        # Assert
        assert food_item.food_item_id == "test-food-item-id"
        assert food_item.fdc_id == 171077
        assert food_item.is_custom is False
    
    def test_food_item_custom_ingredient(self):
        """Test custom food item creation."""
        # Arrange & Act
        custom_food_item = FoodItem(
            name="Homemade Sauce",
            quantity=30.0,
            unit="ml",
            calories=120.0,
            macros=Macros(
                protein=1.0,
                carbs=5.0,
                fat=12.0,
            ),
            food_item_id=str(uuid.uuid4()),
            fdc_id=None,
            is_custom=True
        )
        
        # Assert
        assert custom_food_item.is_custom is True
        assert custom_food_item.fdc_id is None
        assert custom_food_item.food_item_id is not None
    
    def test_food_item_to_dict_includes_edit_fields(self):
        """Test that to_dict includes edit support fields."""
        # Arrange
        food_item = FoodItem(
            name="Test Food",
            quantity=100.0,
            unit="g",
            calories=200.0,
            macros=Macros(protein=10.0, carbs=20.0, fat=8.0),
            food_item_id="test-id",
            fdc_id=12345,
            is_custom=False
        )
        
        # Act
        result = food_item.to_dict()
        
        # Assert
        assert "food_item_id" in result
        assert "fdc_id" in result
        assert "is_custom" in result
        assert result["food_item_id"] == "test-id"
        assert result["fdc_id"] == 12345
        assert result["is_custom"] is False
    
    def test_food_item_to_dict_excludes_none_values(self):
        """Test that to_dict excludes None values for optional fields."""
        # Arrange
        food_item = FoodItem(
            name="Test Food",
            quantity=100.0,
            unit="g",
            calories=200.0,
            macros=Macros(protein=10.0, carbs=20.0, fat=8.0),
            food_item_id=None,
            fdc_id=None,
            is_custom=True
        )
        
        # Act
        result = food_item.to_dict()
        
        # Assert
        assert "food_item_id" not in result
        assert "fdc_id" not in result
        assert "is_custom" in result
        assert result["is_custom"] is True


@pytest.mark.unit
class TestMealEditValidation:
    """Test meal edit validation in domain models."""
    
    def test_meal_post_init_validation_with_edit_fields(self):
        """Test meal validation works with edit fields."""
        # Arrange & Act - should not raise exception
        meal = Meal(
            meal_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            status=MealStatus.READY,
            created_at=datetime.now(),
            image=MealImage(
                image_id=str(uuid.uuid4()),
                format="jpeg",
                size_bytes=100000,
                url="https://example.com/image.jpg"
            ),
            nutrition=Nutrition(
                calories=500.0,
                macros=Macros(protein=30.0, carbs=50.0, fat=20.0),
                food_items=[],
                confidence_score=0.9
            ),
            ready_at=datetime.now(),
            edit_count=5,
            is_manually_edited=True,
            last_edited_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Assert - no exception should be raised
        assert meal.edit_count == 5
        assert meal.is_manually_edited is True
    
    def test_food_item_validation_with_edit_fields(self):
        """Test food item validation works with edit fields."""
        # Arrange & Act - should not raise exception
        food_item = FoodItem(
            name="Test Food",
            quantity=100.0,
            unit="g",
            calories=200.0,
            macros=Macros(protein=10.0, carbs=20.0, fat=8.0),
            confidence=0.95,
            food_item_id=str(uuid.uuid4()),
            fdc_id=12345,
            is_custom=False
        )
        
        # Assert - no exception should be raised
        assert food_item.fdc_id == 12345
        assert food_item.is_custom is False
