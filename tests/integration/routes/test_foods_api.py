"""
Integration tests for foods API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.main import app
from src.api.dependencies.event_bus import get_food_search_event_bus


@pytest.fixture
def client(test_session):
    """Create a test client with mocked dependencies."""
    from src.api.base_dependencies import get_db
    
    def override_get_db():
        try:
            yield test_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestFoodsAPI:
    """Test foods API endpoints."""

    def test_search_foods_success(self, client):
        """Test successful food search."""
        from unittest.mock import AsyncMock, patch
        
        mock_results = {
            "results": [
                {
                    "fdc_id": 171077,
                    "description": "Chicken, broiler or fryers, breast, meat only, raw",
                    "data_type": "Foundation"
                }
            ],
            "query": "chicken",
            "total": 1
        }
        
        # Patch the function where it's used in the route
        with patch('src.api.routes.v1.foods.get_food_search_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_bus.send = AsyncMock(return_value=mock_results)
            mock_get_bus.return_value = mock_bus
            
            response = client.get("/v1/foods/search?q=chicken&limit=10")
            
            assert response.status_code == 200
            data = response.json()
            # Response is a dict with results, not a list
            assert isinstance(data, dict)
            assert "results" in data
            assert isinstance(data["results"], list)
            assert len(data["results"]) == 1

    def test_search_foods_with_limit(self, client):
        """Test food search with custom limit."""
        from unittest.mock import AsyncMock, patch
        
        mock_results = {
            "results": [{"fdc_id": i, "description": f"Food {i}"} for i in range(5)],
            "query": "test",
            "total": 5
        }
        
        with patch('src.api.routes.v1.foods.get_food_search_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_bus.send = AsyncMock(return_value=mock_results)
            mock_get_bus.return_value = mock_bus
            
            response = client.get("/v1/foods/search?q=test&limit=5")
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 5

    def test_search_foods_error_handling(self, client):
        """Test food search error handling."""
        from unittest.mock import AsyncMock, patch
        
        with patch('src.api.routes.v1.foods.get_food_search_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_bus.send = AsyncMock(side_effect=Exception("Search failed"))
            mock_get_bus.return_value = mock_bus
            
            response = client.get("/v1/foods/search?q=chicken")
            
            assert response.status_code == 500
            detail = response.json()["detail"]
            # Handle both string and dict detail formats
            if isinstance(detail, dict):
                assert "Search failed" in detail.get("message", "") or "Search failed" in str(detail)
            else:
                assert "Search failed" in str(detail)

    def test_get_food_details_success(self, client):
        """Test successful food details retrieval."""
        from unittest.mock import AsyncMock, patch
        
        mock_details = {
            "fdc_id": 171077,
            "description": "Chicken, broiler or fryers, breast, meat only, raw",
            "nutrients": [
                {"name": "Protein", "amount": 23.1, "unit": "g"}
            ]
        }
        
        with patch('src.api.routes.v1.foods.get_food_search_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_bus.send = AsyncMock(return_value=mock_details)
            mock_get_bus.return_value = mock_bus
            
            response = client.get("/v1/foods/171077/details")
            
            assert response.status_code == 200
            data = response.json()
            assert data["fdc_id"] == 171077
            assert "description" in data

    def test_get_food_details_error_handling(self, client):
        """Test food details error handling."""
        from unittest.mock import AsyncMock, patch
        
        with patch('src.api.routes.v1.foods.get_food_search_event_bus') as mock_get_bus:
            mock_bus = Mock()
            mock_bus.send = AsyncMock(side_effect=Exception("Details failed"))
            mock_get_bus.return_value = mock_bus
            
            response = client.get("/v1/foods/171077/details")
            
            assert response.status_code == 500
            detail = response.json()["detail"]
            if isinstance(detail, dict):
                assert "Details failed" in detail.get("message", "") or "Details failed" in str(detail)
            else:
                assert "Details failed" in str(detail)

