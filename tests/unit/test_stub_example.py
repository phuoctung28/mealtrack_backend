"""
Example of unit tests with stubs for isolated testing.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal_image import MealImage
from src.domain.model.nutrition import Nutrition
from src.domain.model.macros import Macros


class TestWithStubs:
    """Example of testing with stubs instead of full integration."""
    
    def test_meal_creation_with_stub(self):
        """Test meal creation using stubs."""
        # Create stub meal
        meal = Meal(
            meal_id="test-123",
            status=MealStatus.READY,
            created_at=datetime.now()
        )
        
        # Add stub image
        meal.image = MealImage(
            image_id="img-123",
            format="jpeg",
            size_bytes=1000,
            url="https://example.com/test.jpg"
        )
        
        # Add stub nutrition
        meal.nutrition = Nutrition(
            calories=500,
            macros=Macros(protein=30, carbs=50, fat=20, fiber=5),
            food_items=[],
            confidence_score=0.95
        )
        
        # Verify
        assert meal.meal_id == "test-123"
        assert meal.status == MealStatus.READY
        assert meal.nutrition.calories == 500
    
    def test_repository_with_mock(self):
        """Test repository interactions with mock."""
        # Create mock repository
        mock_repo = Mock()
        mock_repo.find_by_id.return_value = Meal(
            meal_id="test-123",
            status=MealStatus.READY,
            created_at=datetime.now()
        )
        
        # Test
        meal = mock_repo.find_by_id("test-123")
        
        # Verify
        assert meal.meal_id == "test-123"
        mock_repo.find_by_id.assert_called_once_with("test-123")
    
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
        from src.app.handlers.command_handlers.meal_command_handlers import (
            UploadMealImageCommandHandler
        )
        
        # Create all stubs
        stub_image_store = Mock()
        stub_image_store.save.return_value = "mock://test-image.jpg"
        
        stub_meal_repo = Mock()
        stub_meal_repo.save.return_value = None
        
        stub_vision_service = Mock()
        stub_vision_service.analyze.return_value = {"test": "data"}
        
        stub_parser = Mock()
        
        # Create handler with stubs
        handler = UploadMealImageCommandHandler(
            image_store=stub_image_store,
            meal_repository=stub_meal_repo,
            vision_service=stub_vision_service,
            gpt_parser=stub_parser
        )
        
        # Verify handler is created with stubs
        assert handler.image_store == stub_image_store
        assert handler.meal_repository == stub_meal_repo
        assert handler.vision_service == stub_vision_service
        assert handler.gpt_parser == stub_parser