"""
Integration tests for ingredients API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.main import app
from src.api.dependencies.auth import get_current_user_id
from src.api.base_dependencies import get_db


@pytest.fixture
def client(test_session):
    """Create a test client with mocked dependencies."""
    from unittest.mock import Mock
    from src.api.base_dependencies import get_suggestion_orchestration_service
    
    def override_get_db():
        try:
            yield test_session
        finally:
            pass
    
    def override_get_current_user_id():
        return "test_user"
    
    def override_get_suggestion_orchestration_service():
        # Mock the suggestion orchestration service to avoid Redis dependency
        return Mock()
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    app.dependency_overrides[get_suggestion_orchestration_service] = override_get_suggestion_orchestration_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestIngredientsAPI:
    """Test ingredients API endpoints."""

    def test_recognize_ingredient_success(self, client):
        """Test successful ingredient recognition."""
        from src.api.dependencies.event_bus import get_configured_event_bus
        import asyncio
        
        mock_result = {
            "name": "chicken",
            "confidence": 0.95,
            "category": "protein",
            "success": True,
            "message": "Ingredient recognized successfully"
        }
        
        async def mock_send(command):
            return mock_result
        
        mock_bus = Mock()
        mock_bus.send = mock_send
        
        app.dependency_overrides[get_configured_event_bus] = lambda: mock_bus
        
        try:
            response = client.post(
                "/v1/ingredients/recognize",
                json={"image_data": "base64encodedimagedata"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "chicken"
            assert data["confidence"] == 0.95
            assert data["success"] is True
        finally:
            app.dependency_overrides.pop(get_configured_event_bus, None)

    def test_recognize_ingredient_error_handling(self, client):
        """Test ingredient recognition error handling."""
        from src.api.dependencies.event_bus import get_configured_event_bus
        
        async def mock_send(command):
            raise Exception("Recognition failed")
        
        mock_bus = Mock()
        mock_bus.send = mock_send
        
        app.dependency_overrides[get_configured_event_bus] = lambda: mock_bus
        
        try:
            response = client.post(
                "/v1/ingredients/recognize",
                json={"image_data": "base64encodedimagedata"}
            )
            
            # Should handle exception gracefully
            assert response.status_code in [400, 500]
        finally:
            app.dependency_overrides.pop(get_configured_event_bus, None)

    def test_ingredients_health(self, client):
        """Test ingredients health endpoint."""
        response = client.get("/v1/ingredients/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ingredient_recognition"
        assert "features" in data
        assert "photo_ingredient_identification" in data["features"]

