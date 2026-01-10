"""
Integration tests for activities API endpoints.
"""
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.base_dependencies import get_db
from src.api.dependencies.auth import get_current_user_id
from src.api.main import app


@pytest.fixture
def client(test_session):
    """Create a test client with mocked dependencies."""
    from unittest.mock import Mock
    from src.api.base_dependencies import (
        get_suggestion_orchestration_service,
        get_cache_service,
        get_food_cache_service,
    )
    
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
    
    def override_get_cache_service():
        # Return None to disable cache (or return a mock if needed)
        return None
    
    def override_get_food_cache_service():
        # Mock food cache service to avoid Redis dependency
        mock_food_cache = Mock()
        mock_food_cache.get = Mock(return_value=None)
        mock_food_cache.set = Mock(return_value=True)
        return mock_food_cache
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    app.dependency_overrides[get_suggestion_orchestration_service] = override_get_suggestion_orchestration_service
    app.dependency_overrides[get_cache_service] = override_get_cache_service
    app.dependency_overrides[get_food_cache_service] = override_get_food_cache_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestActivitiesAPI:
    """Test activities API endpoints."""

    def test_get_daily_activities_with_date(self, client):
        """Test getting daily activities with specific date."""
        mock_activities = [
            {
                "activity_id": "activity-1",
                "type": "meal",
                "timestamp": "2024-01-15T12:00:00Z"
            }
        ]
        
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_bus.send = Mock(return_value=mock_activities)
            mock_get_bus.return_value = mock_bus
            
            response = client.get("/v1/activities/daily?date=2024-01-15")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_daily_activities_without_date(self, client):
        """Test getting daily activities without date (defaults to today)."""
        mock_activities = []
        
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_bus.send = Mock(return_value=mock_activities)
            mock_get_bus.return_value = mock_bus
            
            response = client.get("/v1/activities/daily")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_daily_activities_invalid_date_format(self, client):
        """Test getting daily activities with invalid date format."""
        response = client.get("/v1/activities/daily?date=invalid-date")
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        # Handle both string and dict detail formats
        if isinstance(detail, dict):
            assert "Invalid date format" in detail.get("message", "")
        else:
            assert "Invalid date format" in str(detail)

    def test_get_daily_activities_error_handling(self, client):
        """Test activities endpoint error handling."""
        from src.api.dependencies.event_bus import get_configured_event_bus
        
        mock_bus = Mock()
        mock_bus.send = Mock(side_effect=Exception("Query failed"))
        
        def override_get_bus():
            return mock_bus
        
        app.dependency_overrides[get_configured_event_bus] = override_get_bus
        
        try:
            response = client.get("/v1/activities/daily")
            
            # Should handle exception gracefully
            assert response.status_code in [400, 500]
        finally:
            app.dependency_overrides.pop(get_configured_event_bus, None)

