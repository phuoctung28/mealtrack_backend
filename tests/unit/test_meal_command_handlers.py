"""
Unit tests for meal command handlers.
"""
import pytest

from src.app.commands.meal import (
    UploadMealImageImmediatelyCommand
)
from src.domain.model.meal import MealStatus


@pytest.mark.unit 
class TestUploadMealImageImmediatelyHandler:
    """Test UploadMealImageImmediatelyCommand handler."""
    
    @pytest.mark.asyncio
    async def test_upload_and_analyze_immediately_success(self, event_bus, sample_image_bytes):
        """Test successful immediate upload and analysis."""
        # Arrange
        command = UploadMealImageImmediatelyCommand(
            user_id="550e8400-e29b-41d4-a716-446655440001",
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
            user_id="550e8400-e29b-41d4-a716-446655440001",
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