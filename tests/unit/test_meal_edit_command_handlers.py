"""
Unit tests for meal edit command handlers.
"""
import pytest
import uuid
from datetime import datetime

from src.api.exceptions import ValidationException, ResourceNotFoundException
from src.app.commands.meal import (
    EditMealCommand,
    AddCustomIngredientCommand,
    FoodItemChange,
    CustomNutritionData
)
from src.app.events.meal import MealEditedEvent
from src.domain.model.meal import MealStatus
from src.domain.model.nutrition import FoodItem, Macros


@pytest.mark.unit
class TestEditMealCommandHandler:
    """Test EditMealCommand handler."""
    
    @pytest.mark.asyncio
    async def test_edit_meal_update_ingredient_quantity(self, event_bus, sample_meal_with_nutrition):
        """Test updating ingredient quantity."""
        # Arrange
        meal = sample_meal_with_nutrition
        original_calories = meal.nutrition.calories
        
        # Get first food item ID
        first_food_item = meal.nutrition.food_items[0]
        food_item_id = str(uuid.uuid4())
        first_food_item.food_item_id = food_item_id
        
        command = EditMealCommand(
            meal_id=meal.meal_id,
            user_id=meal.user_id,
            food_item_changes=[
                FoodItemChange(
                    action="update",
                    food_item_id=food_item_id,
                    quantity=200.0,  # Double the quantity
                    unit="g"
                )
            ]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["success"] is True
        assert result["meal_id"] == meal.meal_id
        assert result["edit_metadata"]["edit_count"] == 1
        assert result["edit_metadata"]["changes_summary"] == "Updated portion"
        
        # Check nutrition was recalculated
        updated_nutrition = result["updated_nutrition"]
        assert updated_nutrition["calories"] > original_calories
        
        # Check events
        assert len(result["events"]) == 1
        event = result["events"][0]
        assert isinstance(event, MealEditedEvent)
        assert event.meal_id == meal.meal_id
        assert event.edit_type == "ingredients_updated"
    
    @pytest.mark.asyncio
    async def test_edit_meal_add_custom_ingredient(self, event_bus, sample_meal_with_nutrition):
        """Test adding a custom ingredient."""
        # Arrange
        meal = sample_meal_with_nutrition
        original_calories = meal.nutrition.calories
        
        command = EditMealCommand(
            meal_id=meal.meal_id,
            user_id=meal.user_id,
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="Homemade Sauce",
                    quantity=50.0,
                    unit="ml",
                    custom_nutrition=CustomNutritionData(
                        calories_per_100g=120.0,
                        protein_per_100g=2.0,
                        carbs_per_100g=8.0,
                        fat_per_100g=10.0,
                    )
                )
            ]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["success"] is True
        assert result["edit_metadata"]["edit_count"] == 1
        assert "Added Homemade Sauce" in result["edit_metadata"]["changes_summary"]
        
        # Check nutrition increased
        updated_nutrition = result["updated_nutrition"]
        assert updated_nutrition["calories"] > original_calories
        
        # Check new food item was added
        updated_food_items = result["updated_food_items"]
        custom_item = next((item for item in updated_food_items if item["name"] == "Homemade Sauce"), None)
        assert custom_item is not None
        assert custom_item["is_custom"] is True
        assert custom_item["quantity"] == 50.0
        assert custom_item["calories"] == 60.0  # 120 * 0.5
    
    @pytest.mark.asyncio
    async def test_edit_meal_remove_ingredient(self, event_bus, sample_meal_with_nutrition):
        """Test removing an ingredient."""
        # Arrange
        meal = sample_meal_with_nutrition
        original_calories = meal.nutrition.calories
        
        # Get first food item ID
        first_food_item = meal.nutrition.food_items[0]
        food_item_id = str(uuid.uuid4())
        first_food_item.food_item_id = food_item_id
        
        command = EditMealCommand(
            meal_id=meal.meal_id,
            user_id=meal.user_id,
            food_item_changes=[
                FoodItemChange(
                    action="remove",
                    food_item_id=food_item_id
                )
            ]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["success"] is True
        assert result["edit_metadata"]["changes_summary"] == "Removed ingredient"
        
        # Check nutrition decreased
        updated_nutrition = result["updated_nutrition"]
        assert updated_nutrition["calories"] < original_calories
        
        # Check food item was removed
        updated_food_items = result["updated_food_items"]
        assert len(updated_food_items) == len(meal.nutrition.food_items) - 1
    
    @pytest.mark.asyncio
    async def test_edit_meal_multiple_changes(self, event_bus, sample_meal_with_nutrition):
        """Test multiple ingredient changes in one operation."""
        # Arrange
        meal = sample_meal_with_nutrition
        
        # Set up food item IDs
        food_item_1_id = str(uuid.uuid4())
        food_item_2_id = str(uuid.uuid4())
        meal.nutrition.food_items[0].food_item_id = food_item_1_id
        meal.nutrition.food_items[1].food_item_id = food_item_2_id
        
        command = EditMealCommand(
            meal_id=meal.meal_id,
            user_id=meal.user_id,
            dish_name="Updated Meal Name",
            food_item_changes=[
                FoodItemChange(
                    action="update",
                    food_item_id=food_item_1_id,
                    quantity=150.0,
                    unit="g"
                ),
                FoodItemChange(
                    action="remove",
                    food_item_id=food_item_2_id
                ),
                FoodItemChange(
                    action="add",
                    name="New Ingredient",
                    quantity=100.0,
                    unit="g",
                    custom_nutrition=CustomNutritionData(
                        calories_per_100g=200.0,
                        protein_per_100g=5.0,
                        carbs_per_100g=15.0,
                        fat_per_100g=8.0
                    )
                )
            ]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["success"] is True
        assert result["edit_metadata"]["edit_count"] == 1
        summary = result["edit_metadata"]["changes_summary"]
        assert "Updated portion" in summary
        assert "Removed ingredient" in summary
        assert "Added New Ingredient" in summary
    
    @pytest.mark.asyncio
    async def test_edit_meal_unauthorized_user(self, event_bus, sample_meal_with_nutrition):
        """Test editing meal with wrong user ID."""
        # Arrange
        meal = sample_meal_with_nutrition
        command = EditMealCommand(
            meal_id=meal.meal_id,
            user_id="different-user-id",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="Test Ingredient",
                    quantity=100.0,
                    unit="g",
                    custom_nutrition=CustomNutritionData(
                        calories_per_100g=100.0,
                        protein_per_100g=5.0,
                        carbs_per_100g=10.0,
                        fat_per_100g=3.0
                    )
                )
            ]
        )
        
        # Act & Assert
        with pytest.raises(ValidationException, match="Meal not found or access denied"):
            await event_bus.send(command)
    
    @pytest.mark.asyncio
    async def test_edit_meal_non_ready_status(self, event_bus, sample_meal_processing):
        """Test editing meal that's not in READY status."""
        # Arrange
        meal = sample_meal_processing
        command = EditMealCommand(
            meal_id=meal.meal_id,
            user_id=meal.user_id,
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="Test Ingredient",
                    quantity=100.0,
                    unit="g",
                    custom_nutrition=CustomNutritionData(
                        calories_per_100g=100.0,
                        protein_per_100g=5.0,
                        carbs_per_100g=10.0,
                        fat_per_100g=3.0
                    )
                )
            ]
        )
        
        # Act & Assert
        with pytest.raises(ValidationException, match="Meal must be in READY status to edit"):
            await event_bus.send(command)
    
    @pytest.mark.asyncio
    async def test_edit_meal_nonexistent_meal(self, event_bus):
        """Test editing non-existent meal."""
        # Arrange
        command = EditMealCommand(
            meal_id="non-existent-meal-id",
            user_id="test-user-id",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="Test Ingredient",
                    quantity=100.0,
                    unit="g",
                    custom_nutrition=CustomNutritionData(
                        calories_per_100g=100.0,
                        protein_per_100g=5.0,
                        carbs_per_100g=10.0,
                        fat_per_100g=3.0
                    )
                )
            ]
        )
        
        # Act & Assert
        with pytest.raises(ValidationException, match="Meal not found or access denied"):
            await event_bus.send(command)


@pytest.mark.unit
class TestAddCustomIngredientCommandHandler:
    """Test AddCustomIngredientCommand handler."""
    
    @pytest.mark.asyncio
    async def test_add_custom_ingredient_success(self, event_bus, sample_meal_with_nutrition):
        """Test successful custom ingredient addition."""
        # Arrange
        meal = sample_meal_with_nutrition
        original_calories = meal.nutrition.calories
        
        command = AddCustomIngredientCommand(
            meal_id=meal.meal_id,
            user_id=meal.user_id,
            name="Homemade Dressing",
            quantity=30.0,
            unit="ml",
            nutrition=CustomNutritionData(
                calories_per_100g=400.0,
                protein_per_100g=1.0,
                carbs_per_100g=5.0,
                fat_per_100g=42.0,
            )
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["success"] is True
        assert result["meal_id"] == meal.meal_id
        assert result["edit_metadata"]["edit_count"] == 1
        
        # Check nutrition increased
        updated_nutrition = result["updated_nutrition"]
        expected_added_calories = 400.0 * 0.3  # 30ml = 30% of 100ml
        assert updated_nutrition["calories"] >= original_calories + expected_added_calories
        
        # Check custom ingredient was added
        updated_food_items = result["updated_food_items"]
        custom_item = next((item for item in updated_food_items if item["name"] == "Homemade Dressing"), None)
        assert custom_item is not None
        assert custom_item["is_custom"] is True
        assert custom_item["quantity"] == 30.0
        assert custom_item["unit"] == "ml"
    
    @pytest.mark.asyncio
    async def test_add_custom_ingredient_unauthorized(self, event_bus, sample_meal_with_nutrition):
        """Test adding custom ingredient with wrong user ID."""
        # Arrange
        meal = sample_meal_with_nutrition
        command = AddCustomIngredientCommand(
            meal_id=meal.meal_id,
            user_id="wrong-user-id",
            name="Test Ingredient",
            quantity=100.0,
            unit="g",
            nutrition=CustomNutritionData(
                calories_per_100g=100.0,
                protein_per_100g=5.0,
                carbs_per_100g=10.0,
                fat_per_100g=3.0
            )
        )
        
        # Act & Assert
        with pytest.raises(ValidationException, match="Meal not found or access denied"):
            await event_bus.send(command)

