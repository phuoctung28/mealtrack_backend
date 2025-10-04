"""
Integration tests for meal edit API endpoints.
"""
import os
import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient

from src.api.main import app
from src.domain.model.meal import MealStatus


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


@pytest.mark.integration
@pytest.mark.skipif(
    not _pinecone_indexes_available(),
    reason="Pinecone indexes not available - skipping meal edit API tests"
)
class TestMealEditAPI:
    """Test meal edit API endpoints."""
    
    @pytest.fixture
    def client(self, test_session, event_bus):
        """Create test client with test database session."""
        from src.api.dependencies.event_bus import get_configured_event_bus
        
        # Override the event bus dependency to use our test event bus
        app.dependency_overrides[get_configured_event_bus] = lambda: event_bus
        
        client = TestClient(app)
        yield client
        
        # Clean up dependency overrides
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_update_meal_ingredients_success(self, client, sample_meal_with_nutrition):
        """Test successful meal ingredients update."""
        # Arrange
        meal = sample_meal_with_nutrition
        id = meal.nutrition.food_items[0].id
        
        request_data = {
            "dish_name": "Updated Grilled Chicken Meal",
            "food_item_changes": [
                {
                    "action": "update",
                    "id": id,
                    "quantity": 200.0,
                    "unit": "g"
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["meal_id"] == meal.meal_id
        assert result["edit_metadata"]["edit_count"] == 1
        assert "updated_nutrition" in result
        assert "updated_food_items" in result
    
    @pytest.mark.asyncio
    async def test_update_meal_ingredients_add_custom(self, client, sample_meal_with_nutrition):
        """Test adding custom ingredient via update endpoint."""
        # Arrange
        meal = sample_meal_with_nutrition
        
        request_data = {
            "food_item_changes": [
                {
                    "action": "add",
                    "name": "Homemade Sauce",
                    "quantity": 50.0,
                    "unit": "ml",
                    "custom_nutrition": {
                        "calories_per_100g": 150.0,
                        "protein_per_100g": 2.0,
                        "carbs_per_100g": 10.0,
                        "fat_per_100g": 12.0,
                    }
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        
        # Check that custom ingredient was added
        updated_food_items = result["updated_food_items"]
        custom_item = next((item for item in updated_food_items if item["name"] == "Homemade Sauce"), None)
        assert custom_item is not None
        assert custom_item["is_custom"] is True
        assert custom_item["quantity"] == 50.0
    
    @pytest.mark.asyncio
    async def test_update_meal_ingredients_remove(self, client, sample_meal_with_nutrition):
        """Test removing ingredient via update endpoint."""
        # Arrange
        meal = sample_meal_with_nutrition
        id = meal.nutrition.food_items[0].id
        original_count = len(meal.nutrition.food_items)
        
        request_data = {
            "food_item_changes": [
                {
                    "action": "remove",
                    "id": id
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        
        # Check that ingredient was removed
        updated_food_items = result["updated_food_items"]
        assert len(updated_food_items) == original_count - 1
    
    @pytest.mark.asyncio
    async def test_update_meal_unauthorized(self, client, sample_meal_with_nutrition):
        """Test meal update with non-existent meal ID (simulates access denied)."""
        # Arrange - use non-existent meal ID to simulate access denied
        request_data = {
            "food_item_changes": [
                {
                    "action": "add",
                    "name": "Test Ingredient",
                    "quantity": 100.0,
                    "unit": "g",
                    "custom_nutrition": {
                        "calories_per_100g": 100.0,
                        "protein_per_100g": 5.0,
                        "carbs_per_100g": 10.0,
                        "fat_per_100g": 3.0
                    }
                }
            ]
        }
        
        # Act
        response = client.put(
            "/v1/meals/non-existent-meal-id/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 404
        error_detail = response.json()["detail"]
        if isinstance(error_detail, dict):
            assert "not found" in error_detail["message"].lower()
        else:
            assert "not found" in error_detail.lower()
    
    @pytest.mark.asyncio
    async def test_update_meal_not_ready(self, client, sample_meal_processing):
        """Test meal update when meal is not in READY status."""
        # Arrange
        meal = sample_meal_processing
        
        request_data = {
            "food_item_changes": [
                {
                    "action": "add",
                    "name": "Test Ingredient",
                    "quantity": 100.0,
                    "unit": "g",
                    "custom_nutrition": {
                        "calories_per_100g": 100.0,
                        "protein_per_100g": 5.0,
                        "carbs_per_100g": 10.0,
                        "fat_per_100g": 3.0
                    }
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 400
        error_detail = response.json()["detail"]
        if isinstance(error_detail, dict):
            assert "ready status" in error_detail["message"].lower()
        else:
            assert "ready status" in error_detail.lower()
    
    @pytest.mark.asyncio
    async def test_update_meal_nonexistent(self, client):
        """Test meal update with non-existent meal ID."""
        # Arrange
        request_data = {
            "food_item_changes": [
                {
                    "action": "add",
                    "name": "Test Ingredient",
                    "quantity": 100.0,
                    "unit": "g",
                    "custom_nutrition": {
                        "calories_per_100g": 100.0,
                        "protein_per_100g": 5.0,
                        "carbs_per_100g": 10.0,
                        "fat_per_100g": 3.0
                    }
                }
            ]
        }
        
        # Act
        response = client.put(
            "/v1/meals/non-existent-meal/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 404
        error_detail = response.json()["detail"]
        if isinstance(error_detail, dict):
            assert "not found" in error_detail["message"].lower()
        else:
            assert "not found" in error_detail.lower()
    
    @pytest.mark.asyncio
    async def test_update_meal_invalid_request_data(self, client, sample_meal_with_nutrition):
        """Test meal update with invalid request data."""
        # Arrange
        meal = sample_meal_with_nutrition
        
        # Invalid request - missing required action field
        request_data = {
            "food_item_changes": [
                {
                    # Missing required "action" field
                    "name": "Test Ingredient",
                    "quantity": 100.0,
                    "unit": "g"
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_multiple_changes_in_one_request(self, client, sample_meal_with_nutrition):
        """Test multiple ingredient changes in a single request."""
        # Arrange
        meal = sample_meal_with_nutrition
        food_item_1_id = meal.nutrition.food_items[0].id
        food_item_2_id = meal.nutrition.food_items[1].id
        
        request_data = {
            "dish_name": "Completely Updated Meal",
            "food_item_changes": [
                {
                    "action": "update",
                    "food_item_id": food_item_1_id,
                    "quantity": 200.0,
                    "unit": "g"
                },
                {
                    "action": "remove",
                    "food_item_id": food_item_2_id
                },
                {
                    "action": "add",
                    "name": "Fresh Herbs",
                    "quantity": 10.0,
                    "unit": "g",
                    "custom_nutrition": {
                        "calories_per_100g": 20.0,
                        "protein_per_100g": 2.0,
                        "carbs_per_100g": 3.0,
                        "fat_per_100g": 0.5,
                    }
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["edit_metadata"]["edit_count"] == 1
        
        # Check all changes were applied
        summary = result["edit_metadata"]["changes_summary"]
        assert "Updated portion" in summary
        assert "Removed ingredient" in summary
        assert "Added Fresh Herbs" in summary
        
        # Check food items
        updated_food_items = result["updated_food_items"]
        herb_item = next((item for item in updated_food_items if item["name"] == "Fresh Herbs"), None)
        assert herb_item is not None
        assert herb_item["is_custom"] is True


@pytest.mark.integration
@pytest.mark.skipif(
    not _pinecone_indexes_available(),
    reason="Pinecone indexes not available - skipping meal edit validation tests"
)
class TestMealEditValidation:
    """Test meal edit validation and error handling."""
    
    @pytest.fixture
    def client(self, test_session, event_bus):
        """Create test client with test database session."""
        from src.api.dependencies.event_bus import get_configured_event_bus
        
        # Override the event bus dependency to use our test event bus
        app.dependency_overrides[get_configured_event_bus] = lambda: event_bus
        
        client = TestClient(app)
        yield client
        
        # Clean up dependency overrides
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_invalid_action_type(self, client, sample_meal_with_nutrition):
        """Test invalid action type in food item change."""
        # Arrange
        meal = sample_meal_with_nutrition
        
        request_data = {
            "food_item_changes": [
                {
                    "action": "invalid_action",
                    "name": "Test Ingredient",
                    "quantity": 100.0,
                    "unit": "g"
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_negative_quantity(self, client, sample_meal_with_nutrition):
        """Test negative quantity validation."""
        # Arrange
        meal = sample_meal_with_nutrition
        
        request_data = {
            "food_item_changes": [
                {
                    "action": "add",
                    "name": "Test Ingredient",
                    "quantity": -50.0,
                    "unit": "g",
                    "custom_nutrition": {
                        "calories_per_100g": 100.0,
                        "protein_per_100g": 5.0,
                        "carbs_per_100g": 10.0,
                        "fat_per_100g": 3.0
                    }
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_invalid_nutrition_values(self, client, sample_meal_with_nutrition):
        """Test invalid nutrition values validation."""
        # Arrange
        meal = sample_meal_with_nutrition
        
        request_data = {
            "food_item_changes": [
                {
                    "action": "add",
                    "name": "Test Ingredient",
                    "quantity": 100.0,
                    "unit": "g",
                    "custom_nutrition": {
                        "calories_per_100g": -100.0,  # Invalid negative calories
                        "protein_per_100g": 5.0,
                        "carbs_per_100g": 10.0,
                        "fat_per_100g": 3.0
                    }
                }
            ]
        }
        
        # Act
        response = client.put(
            f"/v1/meals/{meal.meal_id}/ingredients",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 422

