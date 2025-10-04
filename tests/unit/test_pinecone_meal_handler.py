"""
Unit tests for meal command handlers with Pinecone integration.
"""
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.api.exceptions import ValidationException, ResourceNotFoundException
from src.app.commands.meal import (
    EditMealCommand,
    FoodItemChange,
    CustomNutritionData
)
from src.app.handlers.command_handlers.edit_meal_handler import EditMealCommandHandler
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.nutrition import Nutrition, FoodItem, Macros
from src.infra.services.pinecone_service import NutritionData


def _pinecone_indexes_available():
    """Check if Pinecone indexes are available."""
    if not os.getenv("PINECONE_API_KEY"):
        return False
    try:
        from src.infra.services.pinecone_service import PineconeNutritionService
        service = PineconeNutritionService()
        return service.ingredients_index is not None or service.usda_index is not None
    except (ValueError, Exception):
        return False


@pytest.mark.unit
@pytest.mark.skipif(
    not _pinecone_indexes_available(),
    reason="Pinecone indexes not available - skipping Pinecone meal handler tests"
)
class TestEditMealCommandHandlerWithPinecone:
    """Test EditMealCommandHandler with Pinecone integration."""
    
    @pytest.fixture
    def mock_meal_repository(self):
        """Create mock meal repository."""
        repo = Mock()
        
        # Create a sample meal with existing food items
        existing_food_items = [
            FoodItem(
                id="food-1",
                name="Chicken Breast",
                quantity=100,
                unit="g",
                calories=165,
                macros=Macros(protein=31, carbs=0, fat=3.6),
                confidence=0.9,
                is_custom=False
            )
        ]
        
        nutrition = Nutrition(
            calories=165,
            macros=Macros(protein=31, carbs=0, fat=3.6),
            food_items=existing_food_items,
            confidence_score=0.9
        )
        
        meal = Meal.create(
            meal_id="meal-123",
            user_id="user-1",
            dish_name="Chicken Meal",
            meal_date=datetime.now(),
            image=None,
            status=MealStatus.READY,
            nutrition=nutrition
        )
        
        repo.find_by_id.return_value = meal
        repo.save.return_value = meal
        
        return repo
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.edit_meal_handler.get_pinecone_service')
    async def test_add_ingredient_uses_pinecone_first(self, mock_get_pinecone, mock_meal_repository):
        """Test that adding ingredient uses Pinecone as primary search method."""
        # Arrange
        mock_pinecone_service = Mock()
        mock_pinecone_nutrition = NutritionData(
            calories=130,
            protein=2.7,
            fat=0.3,
            carbs=28,
            fiber=0.4,
            sugar=0.1,
            sodium=1,
            serving_size_g=150
        )
        mock_pinecone_service.get_scaled_nutrition.return_value = mock_pinecone_nutrition
        mock_get_pinecone.return_value = mock_pinecone_service
        
        handler = EditMealCommandHandler(meal_repository=mock_meal_repository)
        
        command = EditMealCommand(
            meal_id="meal-123",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="rice",
                    quantity=150,
                    unit="g"
                )
            ]
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert
        assert result["success"] is True
        mock_pinecone_service.get_scaled_nutrition.assert_called_once_with(
            ingredient_name="rice",
            quantity=150,
            unit="g"
        )
        
        # Check that the nutrition was calculated from Pinecone data
        updated_nutrition = result["updated_nutrition"]
        # Original chicken (165) + rice (130) = 295
        assert updated_nutrition["calories"] == pytest.approx(295, 0.1)
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.edit_meal_handler.get_pinecone_service')
    async def test_add_ingredient_with_fdc_id_overrides_pinecone(self, mock_get_pinecone, mock_meal_repository):
        """Test that explicit fdc_id overrides Pinecone search."""
        # Arrange
        mock_pinecone_service = Mock()
        mock_get_pinecone.return_value = mock_pinecone_service
        
        mock_food_service = Mock()
        mock_food_service.get_food_details = AsyncMock(return_value={
            'description': 'USDA Rice',
            'foodNutrients': [
                {'nutrient': {'id': 1008}, 'amount': 140},  # calories
                {'nutrient': {'id': 1003}, 'amount': 3.0},  # protein
                {'nutrient': {'id': 1005}, 'amount': 30},   # carbs
                {'nutrient': {'id': 1004}, 'amount': 0.5},  # fat
            ]
        })
        
        handler = EditMealCommandHandler(
            meal_repository=mock_meal_repository,
            food_service=mock_food_service
        )
        
        command = EditMealCommand(
            meal_id="meal-123",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="rice",
                    fdc_id=12345,  # Explicit fdc_id
                    quantity=150,
                    unit="g"
                )
            ]
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert
        assert result["success"] is True
        # Pinecone should NOT be called when fdc_id is provided
        mock_pinecone_service.get_scaled_nutrition.assert_not_called()
        # USDA API should be called instead
        mock_food_service.get_food_details.assert_called_once_with(12345)
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.edit_meal_handler.get_pinecone_service')
    async def test_add_ingredient_with_custom_nutrition_overrides_pinecone(self, mock_get_pinecone, mock_meal_repository):
        """Test that custom nutrition overrides Pinecone search."""
        # Arrange
        mock_pinecone_service = Mock()
        mock_get_pinecone.return_value = mock_pinecone_service
        
        handler = EditMealCommandHandler(meal_repository=mock_meal_repository)
        
        command = EditMealCommand(
            meal_id="meal-123",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="custom sauce",
                    quantity=50,
                    unit="g",
                    custom_nutrition=CustomNutritionData(
                        calories_per_100g=200,
                        protein_per_100g=5,
                        carbs_per_100g=10,
                        fat_per_100g=15
                    )
                )
            ]
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert
        assert result["success"] is True
        # Pinecone should NOT be called when custom_nutrition is provided
        mock_pinecone_service.get_scaled_nutrition.assert_not_called()
        
        # Check custom nutrition was used (50g = 0.5 * 200 = 100 calories)
        updated_nutrition = result["updated_nutrition"]
        assert updated_nutrition["calories"] == pytest.approx(265, 0.1)  # 165 + 100
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.edit_meal_handler.get_pinecone_service')
    async def test_add_ingredient_pinecone_fallback_when_not_found(self, mock_get_pinecone, mock_meal_repository):
        """Test behavior when Pinecone doesn't find ingredient."""
        # Arrange
        mock_pinecone_service = Mock()
        mock_pinecone_service.get_scaled_nutrition.return_value = None  # Not found
        mock_get_pinecone.return_value = mock_pinecone_service
        
        handler = EditMealCommandHandler(meal_repository=mock_meal_repository)
        
        command = EditMealCommand(
            meal_id="meal-123",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="unknown food",
                    quantity=100,
                    unit="g"
                )
            ]
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert
        assert result["success"] is True
        mock_pinecone_service.get_scaled_nutrition.assert_called_once()
        
        # Meal should still be valid but only has original item
        updated_food_items = result["updated_food_items"]
        assert len(updated_food_items) == 1  # Only original chicken, unknown food skipped
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.edit_meal_handler.get_pinecone_service')
    async def test_add_ingredient_pinecone_error_handling(self, mock_get_pinecone, mock_meal_repository):
        """Test graceful error handling when Pinecone service fails."""
        # Arrange
        mock_pinecone_service = Mock()
        mock_pinecone_service.get_scaled_nutrition.side_effect = Exception("Pinecone connection error")
        mock_get_pinecone.return_value = mock_pinecone_service
        
        handler = EditMealCommandHandler(meal_repository=mock_meal_repository)
        
        command = EditMealCommand(
            meal_id="meal-123",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="rice",
                    quantity=150,
                    unit="g"
                )
            ]
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert - should not crash, just skip the ingredient
        assert result["success"] is True
        mock_pinecone_service.get_scaled_nutrition.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.edit_meal_handler.get_pinecone_service')
    async def test_priority_order_pinecone_then_fdc_then_custom(self, mock_get_pinecone, mock_meal_repository):
        """Test that priority order is: Pinecone > fdc_id > custom_nutrition."""
        # Arrange
        mock_pinecone_service = Mock()
        mock_pinecone_nutrition = NutritionData(
            calories=100,
            protein=10,
            fat=2,
            carbs=15,
            serving_size_g=100
        )
        mock_pinecone_service.get_scaled_nutrition.return_value = mock_pinecone_nutrition
        mock_get_pinecone.return_value = mock_pinecone_service
        
        handler = EditMealCommandHandler(meal_repository=mock_meal_repository)
        
        # Command has all three: name (Pinecone), fdc_id, and custom_nutrition
        command = EditMealCommand(
            meal_id="meal-123",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="rice",  # Should use Pinecone for this
                    fdc_id=12345,  # Should be ignored
                    quantity=100,
                    unit="g",
                    custom_nutrition=CustomNutritionData(  # Should be ignored
                        calories_per_100g=999,
                        protein_per_100g=99,
                        carbs_per_100g=99,
                        fat_per_100g=99
                    )
                )
            ]
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert
        assert result["success"] is True
        # Pinecone should be called
        mock_pinecone_service.get_scaled_nutrition.assert_called_once_with(
            ingredient_name="rice",
            quantity=100,
            unit="g"
        )
        
        # Nutrition should be from Pinecone (100 + 165 = 265), not custom (999 + 165)
        updated_nutrition = result["updated_nutrition"]
        assert updated_nutrition["calories"] == pytest.approx(265, 0.1)

