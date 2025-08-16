"""
Unit tests for meal command handlers.
"""
import pytest

from src.api.exceptions import ValidationException, ResourceNotFoundException
from src.app.commands.meal import (
    UploadMealImageCommand,
    RecalculateMealNutritionCommand,
    UploadMealImageImmediatelyCommand
)
from src.domain.model.meal import MealStatus


@pytest.mark.unit
class TestUploadMealImageCommandHandler:
    """Test UploadMealImageCommand handler."""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_upload_meal_image_success(self, event_bus, sample_image_bytes):
        """Test successful meal image upload."""
        # Arrange
        command = UploadMealImageCommand(
            user_id="test-user-123",
            file_contents=sample_image_bytes,
            content_type="image/jpeg"
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert "meal_id" in result
        assert result["status"] == MealStatus.PROCESSING.value
        assert "image_url" in result
        assert result["image_url"].startswith("mock://images/")
        assert "events" in result
    
    @pytest.mark.asyncio
    async def test_upload_meal_image_stores_meal_in_repository(
        self, event_bus, meal_repository, sample_image_bytes
    ):
        """Test that uploaded meal is stored in repository."""
        # Arrange
        command = UploadMealImageCommand(
            user_id="test-user-123",
            file_contents=sample_image_bytes,
            content_type="image/jpeg"
        )
        
        # Act
        result = await event_bus.send(command)
        meal_id = result["meal_id"]
        
        # Assert
        stored_meal = meal_repository.find_by_id(meal_id)
        assert stored_meal is not None
        assert stored_meal.status == MealStatus.PROCESSING
        assert stored_meal.image is not None


@pytest.mark.unit
class TestRecalculateMealNutritionCommandHandler:
    """Test RecalculateMealNutritionCommand handler."""
    
    @pytest.mark.asyncio
    async def test_recalculate_nutrition_success(self, event_bus, sample_meal_db):
        """Test successful nutrition recalculation."""
        # Arrange
        command = RecalculateMealNutritionCommand(
            meal_id=sample_meal_db.meal_id,
            weight_grams=200.0  # Double the weight
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["meal_id"] == sample_meal_db.meal_id
        assert result["weight_grams"] == 200.0
        assert "updated_nutrition" in result
        # Original was 500 calories for 100g, now should be 1000 for 200g
        assert result["updated_nutrition"]["calories"] == 1000.0
    
    @pytest.mark.asyncio
    async def test_recalculate_nutrition_meal_not_found(self, event_bus):
        """Test recalculation with non-existent meal."""
        # Arrange
        command = RecalculateMealNutritionCommand(
            meal_id="non-existent-meal",
            weight_grams=100.0
        )
        
        # Act & Assert
        with pytest.raises(ResourceNotFoundException):
            await event_bus.send(command)
    
    @pytest.mark.asyncio
    async def test_recalculate_nutrition_invalid_weight(self, event_bus, sample_meal_db):
        """Test recalculation with invalid weight."""
        # Arrange
        command = RecalculateMealNutritionCommand(
            meal_id=sample_meal_db.meal_id,
            weight_grams=-10.0
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            await event_bus.send(command)


@pytest.mark.unit 
class TestUploadMealImageImmediatelyHandler:
    """Test UploadMealImageImmediatelyCommand handler."""
    
    @pytest.mark.asyncio
    async def test_upload_and_analyze_immediately_success(self, event_bus, sample_image_bytes):
        """Test successful immediate upload and analysis."""
        # Arrange
        command = UploadMealImageImmediatelyCommand(
            user_id="test-user-123",
            file_contents=sample_image_bytes,
            content_type="image/jpeg"
        )
        
        # Act
        meal = await event_bus.send(command)
        
        # Assert
        assert meal.meal_id is not None
        assert meal.status == MealStatus.READY
        assert meal.dish_name == "Grilled Chicken with Rice"
        assert meal.nutrition is not None
        assert meal.nutrition.calories == 650.0
        assert len(meal.nutrition.food_items) == 3
    
    @pytest.mark.asyncio
    async def test_upload_and_analyze_immediately_stores_in_repository(
        self, event_bus, meal_repository, sample_image_bytes
    ):
        """Test that immediately analyzed meal is stored correctly."""
        # Arrange
        command = UploadMealImageImmediatelyCommand(
            user_id="test-user-123",
            file_contents=sample_image_bytes,
            content_type="image/jpeg"
        )
        
        # Act
        meal = await event_bus.send(command)
        
        # Assert
        stored_meal = meal_repository.find_by_id(meal.meal_id)
        assert stored_meal is not None
        assert stored_meal.status == MealStatus.READY
        assert stored_meal.nutrition is not None