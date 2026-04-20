"""
Unit tests for meal edit database model functionality.
"""
import uuid
from datetime import datetime

import pytest

from src.domain.model import Meal as DomainMeal, MealStatus, MealImage, Nutrition, FoodItem, Macros
from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.meal.meal_image import MealImageORM
from src.infra.database.models.nutrition.food_item import FoodItemORM
from src.infra.database.models.nutrition.nutrition import NutritionORM
from src.infra.mappers.meal_mapper import (
    meal_orm_to_domain,
    meal_domain_to_orm,
    food_item_orm_to_domain,
    food_item_domain_to_orm,
)

@pytest.mark.unit
class TestMealDatabaseModelEdit:
    """Test meal database model edit functionality."""

    def test_meal_model_to_domain_includes_edit_fields(self):
        """Test that meal model to_domain includes edit tracking fields."""
        # Arrange
        meal_model = MealORM()
        meal_model.meal_id = str(uuid.uuid4())
        meal_model.user_id = str(uuid.uuid4())
        from src.infra.database.models.enums import MealStatusEnum
        meal_model.status = MealStatusEnum.READY
        meal_model.created_at = datetime.now()
        meal_model.updated_at = datetime.now()
        meal_model.dish_name = "Test Meal"
        meal_model.ready_at = datetime.now()
        meal_model.edit_count = 3
        meal_model.is_manually_edited = True
        meal_model.last_edited_at = datetime.now()

        # Mock image relationship
        image_orm = MealImageORM()
        image_orm.image_id = str(uuid.uuid4())
        image_orm.format = "jpeg"
        image_orm.size_bytes = 100000
        image_orm.width = None
        image_orm.height = None
        image_orm.url = "https://example.com/image.jpg"
        meal_model.image = image_orm

        # Mock nutrition relationship
        nutrition_model = NutritionORM()
        nutrition_model.protein = 30.0
        nutrition_model.carbs = 50.0
        nutrition_model.fat = 20.0
        nutrition_model.fiber = 0.0
        nutrition_model.sugar = 0.0
        nutrition_model.confidence_score = 0.9
        nutrition_model.food_items = []
        meal_model.nutrition = nutrition_model

        # Act
        domain_meal = meal_orm_to_domain(meal_model)

        # Assert
        assert domain_meal.edit_count == 3
        assert domain_meal.is_manually_edited is True
        assert domain_meal.last_edited_at is not None
        assert domain_meal.updated_at is not None

    def test_meal_model_from_domain_includes_edit_fields(self):
        """Test that meal model from_domain includes edit tracking fields."""
        # Arrange
        domain_meal = DomainMeal(
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
            dish_name="Test Meal",
            nutrition=Nutrition(
                macros=Macros(protein=30.0, carbs=50.0, fat=20.0),
                food_items=[],
                confidence_score=0.9
            ),
            ready_at=datetime.now(),
            edit_count=2,
            is_manually_edited=True,
            last_edited_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Act
        meal_model = meal_domain_to_orm(domain_meal)

        # Assert
        assert meal_model.edit_count == 2
        assert meal_model.is_manually_edited is True
        assert meal_model.last_edited_at is not None
        assert meal_model.updated_at is not None

    def test_meal_model_from_domain_defaults_edit_fields(self):
        """Test that meal model from_domain uses defaults for missing edit fields."""
        # Arrange
        domain_meal = DomainMeal(
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
                macros=Macros(protein=30.0, carbs=50.0, fat=20.0),
                food_items=[],
                confidence_score=0.9
            ),
            ready_at=datetime.now()
            # Missing edit fields - should use defaults
        )

        # Act
        meal_model = meal_domain_to_orm(domain_meal)

        # Assert
        assert meal_model.edit_count == 0
        assert meal_model.is_manually_edited is False
        assert meal_model.last_edited_at is None

@pytest.mark.unit
class TestFoodItemDatabaseModelEdit:
    """Test food item database model edit functionality."""

    def test_food_item_model_to_domain_includes_edit_fields(self):
        """Test that food item model to_domain includes edit support fields."""
        # Arrange
        food_item_model = FoodItemORM()
        food_item_model.id = "test-uuid-12345"  # Set UUID for testing
        food_item_model.name = "Grilled Chicken"
        food_item_model.quantity = 150.0
        food_item_model.unit = "g"
        food_item_model.confidence = 0.95
        food_item_model.protein = 46.2
        food_item_model.carbs = 0.0
        food_item_model.fat = 5.4
        food_item_model.fiber = 0.0
        food_item_model.sugar = 0.0
        food_item_model.fdc_id = 171077
        food_item_model.is_custom = False

        # Act
        domain_food_item = food_item_orm_to_domain(food_item_model)

        # Assert
        assert domain_food_item.id == food_item_model.id
        assert domain_food_item.fdc_id == 171077
        assert domain_food_item.is_custom is False

    def test_food_item_model_from_domain_includes_edit_fields(self):
        """Test that food item model from_domain includes edit support fields."""
        # Arrange
        domain_food_item = FoodItem(
            name="Custom Sauce",
            quantity=30.0,
            unit="ml",
            macros=Macros(
                protein=1.0,
                carbs=5.0,
                fat=12.0,
            ),
            confidence=0.8,
            id=str(uuid.uuid4()),
            fdc_id=None,
            is_custom=True
        )

        # Act
        food_item_model = food_item_domain_to_orm(domain_food_item, nutrition_id=1)

        # Assert
        # The database model will have an auto-generated integer ID
        assert food_item_model.fdc_id is None
        assert food_item_model.is_custom is True

    def test_food_item_model_from_domain_defaults_edit_fields(self):
        """Test that food item model from_domain uses defaults for missing edit fields."""
        # Arrange
        domain_food_item = FoodItem(
            id="test-food-item-id",
            name="Basic Food",
            quantity=100.0,
            unit="g",
            macros=Macros(protein=10.0, carbs=20.0, fat=8.0),
            confidence=0.9
            # Missing edit fields - should use defaults
        )

        # Act
        food_item_model = food_item_domain_to_orm(domain_food_item, nutrition_id=1)

        # Assert
        assert food_item_model.fdc_id is None
        assert food_item_model.is_custom is False

    def test_food_item_model_handles_none_values(self):
        """Test that food item model handles None values correctly."""
        # Arrange
        food_item_model = FoodItemORM()
        food_item_model.id = "test-uuid-67890"  # Set UUID for testing
        food_item_model.name = "Test Food"
        food_item_model.quantity = 100.0
        food_item_model.unit = "g"
        food_item_model.confidence = 0.9
        food_item_model.protein = 10.0
        food_item_model.carbs = 20.0
        food_item_model.fat = 8.0
        food_item_model.fiber = 0.0
        food_item_model.sugar = 0.0
        food_item_model.fdc_id = None
        food_item_model.is_custom = False

        # Act
        domain_food_item = food_item_orm_to_domain(food_item_model)

        # Assert
        assert domain_food_item.id is not None  # Should have the database ID
        assert domain_food_item.fdc_id is None
        assert domain_food_item.is_custom is False

@pytest.mark.unit
class TestMealEditDatabaseIntegration:
    """Test meal edit database integration functionality."""

    def test_meal_roundtrip_with_edit_fields(self):
        """Test that meal can be converted to/from domain with edit fields intact."""
        # Arrange
        original_domain_meal = DomainMeal(
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
            dish_name="Test Meal",
            nutrition=Nutrition(
                macros=Macros(protein=30.0, carbs=50.0, fat=20.0),
                food_items=[
                    FoodItem(
                        name="Test Food",
                        quantity=100.0,
                        unit="g",
                        macros=Macros(protein=10.0, carbs=20.0, fat=8.0),
                        id=str(uuid.uuid4()),
                        fdc_id=12345,
                        is_custom=False
                    )
                ],
                confidence_score=0.9
            ),
            ready_at=datetime.now(),
            edit_count=3,
            is_manually_edited=True,
            last_edited_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Act
        meal_model = meal_domain_to_orm(original_domain_meal)

        # Mock the image relationship for to_domain conversion
        image_orm = MealImageORM()
        image_orm.image_id = original_domain_meal.image.image_id
        image_orm.format = original_domain_meal.image.format
        image_orm.size_bytes = original_domain_meal.image.size_bytes
        image_orm.width = original_domain_meal.image.width
        image_orm.height = original_domain_meal.image.height
        image_orm.url = original_domain_meal.image.url
        meal_model.image = image_orm

        converted_domain_meal = meal_orm_to_domain(meal_model)

        # Assert
        assert converted_domain_meal.meal_id == original_domain_meal.meal_id
        assert converted_domain_meal.edit_count == original_domain_meal.edit_count
        assert converted_domain_meal.is_manually_edited == original_domain_meal.is_manually_edited
        assert converted_domain_meal.last_edited_at == original_domain_meal.last_edited_at
        assert converted_domain_meal.updated_at == original_domain_meal.updated_at

    def test_food_item_roundtrip_with_edit_fields(self):
        """Test that food item can be converted to/from domain with edit fields intact."""
        # Arrange
        original_domain_food_item = FoodItem(
            name="Test Food",
            quantity=150.0,
            unit="g",
            macros=Macros(protein=25.0, carbs=10.0, fat=15.0),
            confidence=0.95,
            id=str(uuid.uuid4()),
            fdc_id=54321,
            is_custom=True
        )

        # Act
        food_item_model = food_item_domain_to_orm(original_domain_food_item, nutrition_id=1)
        converted_domain_food_item = food_item_orm_to_domain(food_item_model)

        # Assert
        assert converted_domain_food_item.name == original_domain_food_item.name
        # ID conversion: string domain ID -> int DB ID -> string domain ID
        assert converted_domain_food_item.fdc_id == original_domain_food_item.fdc_id
        assert converted_domain_food_item.is_custom == original_domain_food_item.is_custom
        assert converted_domain_food_item.quantity == original_domain_food_item.quantity
        assert converted_domain_food_item.calories == original_domain_food_item.calories
