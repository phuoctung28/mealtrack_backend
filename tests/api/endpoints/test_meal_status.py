import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime

from main import app
from domain.model.meal import Meal, MealStatus
from domain.model.meal_image import MealImage
from app.handlers.meal_handler import MealHandler

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_meal_handler():
    """Create a mock meal handler."""
    with patch("api.dependencies.get_meal_handler") as mock:
        handler = MagicMock(spec=MealHandler)
        mock.return_value = handler
        yield handler

@pytest.fixture
def test_meal():
    """Create a test meal."""
    meal_id = str(uuid.uuid4())
    image = MealImage(
        image_id=str(uuid.uuid4()),
        format="jpeg",
        size_bytes=1000,
        width=100,
        height=100
    )
    
    return Meal(
        meal_id=meal_id,
        status=MealStatus.PROCESSING,
        created_at=datetime.now(),
        image=image
    )

class TestMealStatusEndpoints:
    """Tests for the meal status endpoints."""
    
    def test_get_meal(self, test_client, mock_meal_handler, test_meal):
        """Test getting a meal by ID."""
        # Arrange
        mock_meal_handler.get_meal.return_value = test_meal
        
        # Act
        response = test_client.get(f"/v1/meals/{test_meal.meal_id}")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["meal_id"] == test_meal.meal_id
        assert response.json()["status"] == "PROCESSING"
        mock_meal_handler.get_meal.assert_called_once_with(test_meal.meal_id)
    
    def test_get_meal_not_found(self, test_client, mock_meal_handler):
        """Test getting a non-existent meal."""
        # Arrange
        meal_id = str(uuid.uuid4())
        mock_meal_handler.get_meal.return_value = None
        
        # Act
        response = test_client.get(f"/v1/meals/{meal_id}")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        mock_meal_handler.get_meal.assert_called_once_with(meal_id)
    
    def test_get_meal_status(self, test_client, mock_meal_handler, test_meal):
        """Test getting only the status of a meal."""
        # Arrange
        mock_meal_handler.get_meal.return_value = test_meal
        
        # Act
        response = test_client.get(f"/v1/meals/{test_meal.meal_id}/status")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["meal_id"] == test_meal.meal_id
        assert response.json()["status"] == "PROCESSING"
        assert "status_message" in response.json()
        mock_meal_handler.get_meal.assert_called_once_with(test_meal.meal_id)
    
    def test_get_meal_status_not_found(self, test_client, mock_meal_handler):
        """Test getting the status of a non-existent meal."""
        # Arrange
        meal_id = str(uuid.uuid4())
        mock_meal_handler.get_meal.return_value = None
        
        # Act
        response = test_client.get(f"/v1/meals/{meal_id}/status")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        mock_meal_handler.get_meal.assert_called_once_with(meal_id) 