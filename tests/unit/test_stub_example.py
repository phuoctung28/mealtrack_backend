"""
Example of unit tests with stubs for isolated testing.
"""
from datetime import datetime
from unittest.mock import Mock, MagicMock

import pytest

from src.domain.model.macros import Macros
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.model.nutrition import Nutrition


class TestWithStubs:
    """Example of testing with stubs instead of full integration."""
    
    def test_meal_creation_with_stub(self):
        """Test meal creation using stubs."""
        # Create stub image first
        stub_image = MealImage(
            image_id="123e4567-e89b-12d3-a456-426614174000",
            format="jpeg",
            size_bytes=1000,
            url="https://example.com/test.jpg"
        )
        
        # Create stub nutrition
        stub_nutrition = Nutrition(
            calories=500,
            macros=Macros(protein=30, carbs=50, fat=20),
            food_items=[],
            confidence_score=0.95
        )
        
        # Create stub meal with all required fields
        meal = Meal(
            meal_id="123e4567-e89b-12d3-a456-426614174001",
            user_id="123e4567-e89b-12d3-a456-426614174000",
            status=MealStatus.READY,
            created_at=datetime.now(),
            image=stub_image,
            nutrition=stub_nutrition,
            dish_name="Test Meal",
            ready_at=datetime.now()
        )
        
        # Verify
        assert meal.meal_id == "123e4567-e89b-12d3-a456-426614174001"
        assert meal.status == MealStatus.READY
        assert meal.nutrition.calories == 500
    
    def test_repository_with_mock(self):
        """Test repository interactions with mock."""
        # Create stub image
        stub_image = MealImage(
            image_id="123e4567-e89b-12d3-a456-426614174000",
            format="jpeg",
            size_bytes=1000,
            url="https://example.com/test.jpg"
        )
        
        # Create mock repository
        mock_repo = Mock()
        mock_repo.find_by_id.return_value = Meal(
            meal_id="123e4567-e89b-12d3-a456-426614174001",
            user_id="123e4567-e89b-12d3-a456-426614174000",
            status=MealStatus.READY,
            created_at=datetime.now(),
            image=stub_image,
            nutrition=Nutrition(
                calories=500,
                macros=Macros(protein=30, carbs=50, fat=20),
                food_items=[],
                confidence_score=0.95
            ),
            dish_name="Test Meal",
            ready_at=datetime.now()
        )
        
        # Test
        meal = mock_repo.find_by_id("123e4567-e89b-12d3-a456-426614174001")
        
        # Verify
        assert meal.meal_id == "123e4567-e89b-12d3-a456-426614174001"
        mock_repo.find_by_id.assert_called_once_with("123e4567-e89b-12d3-a456-426614174001")
    
    def test_service_with_stub(self):
        """Test service with stubbed dependencies."""
        # Create stub vision service
        stub_vision_service = MagicMock()
        stub_vision_service.analyze.return_value = {
            "structured_data": {
                "dish_name": "Test Meal",
                "total_calories": 500
            }
        }
        
        # Test
        result = stub_vision_service.analyze(b"image-data")
        
        # Verify
        assert result["structured_data"]["dish_name"] == "Test Meal"
        assert result["structured_data"]["total_calories"] == 500
        stub_vision_service.analyze.assert_called_once()


@pytest.mark.unit
class TestHandlerStubs:
    """Example of testing handlers with stubs."""

    def test_handler_with_stubbed_dependencies(self):
        """Test handler with all dependencies stubbed."""
        from src.app.handlers.command_handlers.edit_meal_handler import (
            EditMealCommandHandler
        )

        # Create all stubs
        stub_meal_repo = Mock()
        stub_meal_repo.save.return_value = None

        stub_food_service = Mock()

        # Create handler with stubs
        handler = EditMealCommandHandler(
            meal_repository=stub_meal_repo,
            food_service=stub_food_service,
            nutrition_calculator=None
        )

        # Verify handler is created with stubs
        assert handler.meal_repository == stub_meal_repo
        assert handler.food_service == stub_food_service