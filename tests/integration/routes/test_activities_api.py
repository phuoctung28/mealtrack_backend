"""
Integration tests for activities API endpoints.
"""
import pytest
from datetime import datetime
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
        assert "Invalid date format" in response.json()["detail"]

    def test_get_daily_activities_error_handling(self, client):
        """Test activities endpoint error handling."""
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_bus.send = Mock(side_effect=Exception("Query failed"))
            mock_get_bus.return_value = mock_bus
            
            response = client.get("/v1/activities/daily")
            
            # Should handle exception gracefully
            assert response.status_code in [400, 500]

