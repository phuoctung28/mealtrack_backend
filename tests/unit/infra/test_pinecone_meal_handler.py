"""
Unit tests for meal command handlers with Pinecone integration.
"""
import os
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import pytest

from src.app.commands.meal import (
    EditMealCommand,
    FoodItemChange,
    CustomNutritionData
)
from src.app.handlers.command_handlers.edit_meal_command_handler import EditMealCommandHandler
from src.domain.model import Meal, MealStatus, Nutrition, FoodItem, Macros, MealImage
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
        
        # Create meal using Meal constructor (Meal.create doesn't exist)
        meal = Meal(
            meal_id="123e4567-e89b-12d3-a456-426614174123",
            user_id="123e4567-e89b-12d3-a456-426614174000",
            status=MealStatus.READY,
            created_at=datetime.now(),
            image=MealImage(
                image_id="123e4567-e89b-12d3-a456-426614174002",
                format="jpeg",
                size_bytes=100000,
                url="https://example.com/image.jpg"
            ),
            dish_name="Chicken Meal",
            nutrition=nutrition,
            ready_at=datetime.now()
        )
        
        repo.find_by_id.return_value = meal
        repo.save.return_value = meal
        
        return repo
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.edit_meal_command_handler.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.edit_meal_command_handler.get_pinecone_service')
    @patch('src.domain.services.nutrition_calculation_service.NutritionCalculationService.get_nutrition_for_ingredient')
    async def test_add_ingredient_with_fdc_id_overrides_pinecone(self, mock_get_nutrition, mock_get_pinecone, mock_meal_repository):
        """Test that explicit fdc_id overrides Pinecone search."""
        # Arrange
        from src.domain.services.nutrition_calculation_service import ScaledNutritionResult
        
        mock_pinecone_service = Mock()
        mock_get_pinecone.return_value = mock_pinecone_service
        
        # Mock nutrition service to return proper ScaledNutritionResult when fdc_id is provided
        mock_get_nutrition.return_value = ScaledNutritionResult(
            calories=210.0,  # 140 * 1.5 (150g / 100g)
            protein=4.5,     # 3.0 * 1.5
            carbs=45.0,      # 30 * 1.5
            fat=0.75         # 0.5 * 1.5
        )
        
        mock_food_service = Mock()
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
        # Verify get_nutrition_for_ingredient was called with fdc_id
        mock_get_nutrition.assert_called_once()
        call_args = mock_get_nutrition.call_args
        assert call_args[1]['fdc_id'] == 12345  # fdc_id should be passed
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.edit_meal_command_handler.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.edit_meal_command_handler.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.edit_meal_command_handler.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.edit_meal_command_handler.get_pinecone_service')
    async def test_priority_order_pinecone_then_fdc_then_custom(self, mock_get_pinecone, mock_meal_repository):
        """Test that priority order is: custom_nutrition > fdc_id > Pinecone."""
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
        # Actual priority: custom_nutrition (1) > fdc_id (2) > Pinecone (3)
        command = EditMealCommand(
            meal_id="meal-123",
            food_item_changes=[
                FoodItemChange(
                    action="add",
                    name="rice",
                    fdc_id=12345,  # Should be ignored because custom_nutrition is provided
                    quantity=100,
                    unit="g",
                    custom_nutrition=CustomNutritionData(  # Priority 1: Should be used first
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
        # Custom nutrition should be used, so Pinecone should NOT be called
        mock_pinecone_service.get_scaled_nutrition.assert_not_called()
        
        # Nutrition should be from custom (999 + 165 = 1164), not Pinecone (100 + 165 = 265)
        updated_nutrition = result["updated_nutrition"]
        assert updated_nutrition["calories"] == pytest.approx(1164, 0.1)  # Original 165 + custom 999

