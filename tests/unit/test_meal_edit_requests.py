"""
Unit tests for meal edit request validation.
"""
import pytest
from pydantic import ValidationError

from src.api.schemas.request.meal_requests import (
    FoodItemChangeRequest,
    CustomNutritionRequest,
    EditMealIngredientsRequest,
    AddCustomIngredientRequest
)


@pytest.mark.unit
class TestFoodItemChangeRequest:
    """Test FoodItemChangeRequest validation."""
    
    def test_valid_add_request(self):
        """Test valid add request."""
        # Arrange & Act
        request = FoodItemChangeRequest(
            action="add",
            name="Test Food",
            quantity=100.0,
            unit="g",
            custom_nutrition=CustomNutritionRequest(
                calories_per_100g=200.0,
                protein_per_100g=10.0,
                carbs_per_100g=20.0,
                fat_per_100g=8.0,
            )
        )
        
        # Assert
        assert request.action == "add"
        assert request.name == "Test Food"
        assert request.quantity == 100.0
        assert request.unit == "g"
        assert request.custom_nutrition.calories_per_100g == 200.0
    
    def test_valid_update_request(self):
        """Test valid update request."""
        # Arrange & Act
        request = FoodItemChangeRequest(
            action="update",
            food_item_id="test-food-item-id",
            quantity=150.0,
            unit="g"
        )
        
        # Assert
        assert request.action == "update"
        assert request.food_item_id == "test-food-item-id"
        assert request.quantity == 150.0
        assert request.unit == "g"
    
    def test_valid_remove_request(self):
        """Test valid remove request."""
        # Arrange & Act
        request = FoodItemChangeRequest(
            action="remove",
            food_item_id="test-food-item-id"
        )
        
        # Assert
        assert request.action == "remove"
        assert request.food_item_id == "test-food-item-id"
    
    def test_invalid_action(self):
        """Test invalid action value."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FoodItemChangeRequest(
                action="invalid_action",
                name="Test Food",
                quantity=100.0,
                unit="g"
            )
    
    def test_negative_quantity(self):
        """Test negative quantity validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FoodItemChangeRequest(
                action="add",
                name="Test Food",
                quantity=-50.0,
                unit="g"
            )
    
    def test_zero_quantity(self):
        """Test zero quantity validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FoodItemChangeRequest(
                action="add",
                name="Test Food",
                quantity=0.0,
                unit="g"
            )
    
    def test_quantity_too_large(self):
        """Test quantity too large validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FoodItemChangeRequest(
                action="add",
                name="Test Food",
                quantity=15000.0,  # Over 10000 limit
                unit="g"
            )
    
    def test_empty_name(self):
        """Test empty name validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FoodItemChangeRequest(
                action="add",
                name="",
                quantity=100.0,
                unit="g"
            )
    
    def test_name_too_long(self):
        """Test name too long validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FoodItemChangeRequest(
                action="add",
                name="a" * 201,  # Over 200 character limit
                quantity=100.0,
                unit="g"
            )
    
    def test_empty_unit(self):
        """Test empty unit validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FoodItemChangeRequest(
                action="add",
                name="Test Food",
                quantity=100.0,
                unit=""
            )
    
    def test_unit_too_long(self):
        """Test unit too long validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FoodItemChangeRequest(
                action="add",
                name="Test Food",
                quantity=100.0,
                unit="a" * 21  # Over 20 character limit
            )


@pytest.mark.unit
class TestCustomNutritionRequest:
    """Test CustomNutritionRequest validation."""
    
    def test_valid_nutrition_request(self):
        """Test valid nutrition request."""
        # Arrange & Act
        request = CustomNutritionRequest(
            calories_per_100g=200.0,
            protein_per_100g=15.0,
            carbs_per_100g=25.0,
            fat_per_100g=8.0,
        )
        
        # Assert
        assert request.calories_per_100g == 200.0
        assert request.protein_per_100g == 15.0
        assert request.carbs_per_100g == 25.0
        assert request.fat_per_100g == 8.0
    
    def test_negative_calories(self):
        """Test negative calories validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            CustomNutritionRequest(
                calories_per_100g=-100.0,
                protein_per_100g=15.0,
                carbs_per_100g=25.0,
                fat_per_100g=8.0
            )
    
    def test_calories_too_high(self):
        """Test calories too high validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            CustomNutritionRequest(
                calories_per_100g=1500.0,  # Over 1000 limit
                protein_per_100g=15.0,
                carbs_per_100g=25.0,
                fat_per_100g=8.0
            )
    
    def test_negative_protein(self):
        """Test negative protein validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            CustomNutritionRequest(
                calories_per_100g=200.0,
                protein_per_100g=-5.0,
                carbs_per_100g=25.0,
                fat_per_100g=8.0
            )
    
    def test_protein_too_high(self):
        """Test protein too high validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            CustomNutritionRequest(
                calories_per_100g=200.0,
                protein_per_100g=150.0,  # Over 100 limit
                carbs_per_100g=25.0,
                fat_per_100g=8.0
            )


@pytest.mark.unit
class TestEditMealIngredientsRequest:
    """Test EditMealIngredientsRequest validation."""
    
    def test_valid_edit_request(self):
        """Test valid edit meal ingredients request."""
        # Arrange & Act
        request = EditMealIngredientsRequest(
            dish_name="Updated Meal Name",
            food_item_changes=[
                FoodItemChangeRequest(
                    action="add",
                    name="New Food",
                    quantity=100.0,
                    unit="g",
                    custom_nutrition=CustomNutritionRequest(
                        calories_per_100g=200.0,
                        protein_per_100g=10.0,
                        carbs_per_100g=20.0,
                        fat_per_100g=8.0
                    )
                )
            ]
        )
        
        # Assert
        assert request.dish_name == "Updated Meal Name"
        assert len(request.food_item_changes) == 1
        assert request.food_item_changes[0].action == "add"
    
    def test_valid_edit_request_without_dish_name(self):
        """Test valid edit request without dish name."""
        # Arrange & Act
        request = EditMealIngredientsRequest(
            food_item_changes=[
                FoodItemChangeRequest(
                    action="update",
                    food_item_id="test-id",
                    quantity=150.0,
                    unit="g"
                )
            ]
        )
        
        # Assert
        assert request.dish_name is None
        assert len(request.food_item_changes) == 1
    
    def test_empty_food_item_changes(self):
        """Test empty food item changes validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            EditMealIngredientsRequest(
                food_item_changes=[]
            )
    
    def test_dish_name_too_long(self):
        """Test dish name too long validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            EditMealIngredientsRequest(
                dish_name="a" * 201,  # Over 200 character limit
                food_item_changes=[
                    FoodItemChangeRequest(
                        action="add",
                        name="Test Food",
                        quantity=100.0,
                        unit="g"
                    )
                ]
            )
    
    def test_empty_dish_name(self):
        """Test empty dish name validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            EditMealIngredientsRequest(
                dish_name="",
                food_item_changes=[
                    FoodItemChangeRequest(
                        action="add",
                        name="Test Food",
                        quantity=100.0,
                        unit="g"
                    )
                ]
            )


@pytest.mark.unit
class TestAddCustomIngredientRequest:
    """Test AddCustomIngredientRequest validation."""
    
    def test_valid_custom_ingredient_request(self):
        """Test valid custom ingredient request."""
        # Arrange & Act
        request = AddCustomIngredientRequest(
            name="Homemade Sauce",
            quantity=50.0,
            unit="ml",
            nutrition=CustomNutritionRequest(
                calories_per_100g=150.0,
                protein_per_100g=2.0,
                carbs_per_100g=10.0,
                fat_per_100g=12.0,
            )
        )
        
        # Assert
        assert request.name == "Homemade Sauce"
        assert request.quantity == 50.0
        assert request.unit == "ml"
        assert request.nutrition.calories_per_100g == 150.0
    
    def test_empty_name(self):
        """Test empty name validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            AddCustomIngredientRequest(
                name="",
                quantity=50.0,
                unit="ml",
                nutrition=CustomNutritionRequest(
                    calories_per_100g=150.0,
                    protein_per_100g=2.0,
                    carbs_per_100g=10.0,
                    fat_per_100g=12.0
                )
            )
    
    def test_name_too_long(self):
        """Test name too long validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            AddCustomIngredientRequest(
                name="a" * 201,  # Over 200 character limit
                quantity=50.0,
                unit="ml",
                nutrition=CustomNutritionRequest(
                    calories_per_100g=150.0,
                    protein_per_100g=2.0,
                    carbs_per_100g=10.0,
                    fat_per_100g=12.0
                )
            )
    
    def test_negative_quantity(self):
        """Test negative quantity validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            AddCustomIngredientRequest(
                name="Test Ingredient",
                quantity=-25.0,
                unit="ml",
                nutrition=CustomNutritionRequest(
                    calories_per_100g=150.0,
                    protein_per_100g=2.0,
                    carbs_per_100g=10.0,
                    fat_per_100g=12.0
                )
            )
    
    def test_quantity_too_large(self):
        """Test quantity too large validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            AddCustomIngredientRequest(
                name="Test Ingredient",
                quantity=15000.0,  # Over 10000 limit
                unit="ml",
                nutrition=CustomNutritionRequest(
                    calories_per_100g=150.0,
                    protein_per_100g=2.0,
                    carbs_per_100g=10.0,
                    fat_per_100g=12.0
                )
            )
    
    def test_empty_unit(self):
        """Test empty unit validation."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            AddCustomIngredientRequest(
                name="Test Ingredient",
                quantity=50.0,
                unit="",
                nutrition=CustomNutritionRequest(
                    calories_per_100g=150.0,
                    protein_per_100g=2.0,
                    carbs_per_100g=10.0,
                    fat_per_100g=12.0
                )
            )

