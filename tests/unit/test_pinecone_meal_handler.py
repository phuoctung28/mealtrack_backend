"""
Unit tests for meal command handlers with Pinecone integration.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.api.exceptions import ValidationException, ResourceNotFoundException
from src.app.commands.meal import (
    EditMealCommand,
    RecalculateMealNutritionCommand,
    FoodItemChange,
    CustomNutritionData
)
from src.app.handlers.command_handlers.meal_command_handlers import (
    EditMealCommandHandler,
    RecalculateMealNutritionCommandHandler
)
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.nutrition import Nutrition, FoodItem, Macros
from src.infra.services.pinecone_service import NutritionData


@pytest.mark.unit
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
    @patch('src.app.handlers.command_handlers.meal_command_handlers.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.meal_command_handlers.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.meal_command_handlers.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.meal_command_handlers.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.meal_command_handlers.get_pinecone_service')
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
    @patch('src.app.handlers.command_handlers.meal_command_handlers.get_pinecone_service')
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


@pytest.mark.unit
class TestRecalculateMealNutritionCommandHandlerWithPinecone:
    """Test RecalculateMealNutritionCommandHandler with Pinecone integration."""
    
    @pytest.fixture
    def mock_meal_repository_with_items(self):
        """Create mock meal repository with food items."""
        repo = Mock()
        
        food_items = [
            FoodItem(
                id="food-1",
                name="chicken breast",
                quantity=200,
                unit="g",
                calories=330,
                macros=Macros(protein=62, carbs=0, fat=7.2),
                confidence=0.9,
                is_custom=False
            ),
            FoodItem(
                id="food-2",
                name="rice",
                quantity=150,
                unit="g",
                calories=195,
                macros=Macros(protein=4.05, carbs=42, fat=0.45),
                confidence=0.9,
                is_custom=False
            )
        ]
        
        nutrition = Nutrition(
            calories=525,
            macros=Macros(protein=66.05, carbs=42, fat=7.65),
            food_items=food_items,
            confidence_score=0.9
        )
        
        meal = Meal.create(
            meal_id="meal-123",
            user_id="user-1",
            dish_name="Chicken and Rice",
            meal_date=datetime.now(),
            image=None,
            status=MealStatus.READY,
            nutrition=nutrition
        )
        
        repo.find_by_id.return_value = meal
        repo.save.return_value = meal
        
        return repo
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.meal_command_handlers.get_pinecone_service')
    async def test_recalculate_uses_pinecone_for_fresh_data(self, mock_get_pinecone, mock_meal_repository_with_items):
        """Test that recalculation uses Pinecone to get fresh nutrition data."""
        # Arrange
        mock_pinecone_service = Mock()
        mock_total_nutrition = NutritionData(
            calories=500,
            protein=65,
            fat=7.5,
            carbs=40,
            fiber=1,
            sugar=0.5,
            sodium=100,
            serving_size_g=350
        )
        mock_pinecone_service.calculate_total_nutrition.return_value = mock_total_nutrition
        mock_get_pinecone.return_value = mock_pinecone_service
        
        handler = RecalculateMealNutritionCommandHandler(meal_repository=mock_meal_repository_with_items)
        
        command = RecalculateMealNutritionCommand(
            meal_id="meal-123",
            weight_grams=350
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert
        assert result["meal_id"] == "meal-123"
        mock_pinecone_service.calculate_total_nutrition.assert_called_once()
        
        # Check that Pinecone calculated nutrition was used
        call_args = mock_pinecone_service.calculate_total_nutrition.call_args[0][0]
        assert len(call_args) == 2  # Two ingredients
        assert call_args[0]['name'] == 'chicken breast'
        assert call_args[0]['quantity'] == 200
        assert call_args[1]['name'] == 'rice'
        assert call_args[1]['quantity'] == 150
        
        # Check result uses Pinecone data
        updated_nutrition = result["updated_nutrition"]
        assert updated_nutrition["calories"] == 500
        assert updated_nutrition["protein"] == 65
    
    @pytest.mark.asyncio
    @patch('src.app.handlers.command_handlers.meal_command_handlers.get_pinecone_service')
    async def test_recalculate_fallback_to_scaling_on_pinecone_error(self, mock_get_pinecone, mock_meal_repository_with_items):
        """Test that recalculation falls back to scaling when Pinecone fails."""
        # Arrange
        mock_pinecone_service = Mock()
        mock_pinecone_service.calculate_total_nutrition.side_effect = Exception("Pinecone error")
        mock_get_pinecone.return_value = mock_pinecone_service
        
        handler = RecalculateMealNutritionCommandHandler(meal_repository=mock_meal_repository_with_items)
        
        command = RecalculateMealNutritionCommand(
            meal_id="meal-123",
            weight_grams=350
        )
        
        # Act
        result = await handler.handle(command)
        
        # Assert - should still succeed with fallback scaling
        assert result["meal_id"] == "meal-123"
        mock_pinecone_service.calculate_total_nutrition.assert_called_once()
        
        # Should have valid nutrition (scaled)
        updated_nutrition = result["updated_nutrition"]
        assert "calories" in updated_nutrition
        assert updated_nutrition["calories"] > 0
    
    @pytest.mark.asyncio
    async def test_recalculate_fails_when_no_food_items(self):
        """Test that recalculation fails when meal has no food items."""
        # Arrange
        repo = Mock()
        meal = Meal.create(
            meal_id="meal-123",
            user_id="user-1",
            dish_name="Empty Meal",
            meal_date=datetime.now(),
            image=None,
            status=MealStatus.READY,
            nutrition=Nutrition(
                calories=0,
                macros=Macros(protein=0, carbs=0, fat=0),
                food_items=[],
                confidence_score=0
            )
        )
        repo.find_by_id.return_value = meal
        
        handler = RecalculateMealNutritionCommandHandler(meal_repository=repo)
        
        command = RecalculateMealNutritionCommand(
            meal_id="meal-123",
            weight_grams=350
        )
        
        # Act & Assert
        with pytest.raises(ValidationException, match="no food items"):
            await handler.handle(command)
