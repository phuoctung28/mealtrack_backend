import asyncio
import os
from typing import Generator

import httpx
import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (slow)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast)"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def base_url() -> str:
    """Get the base URL for API testing."""
    return os.environ.get("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session") 
def test_client(base_url: str) -> Generator[httpx.Client, None, None]:
    """Create a test client for the entire test session."""
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def api_client(test_client: httpx.Client) -> httpx.Client:
    """Provide API client for individual tests."""
    return test_client


# Common test data fixtures
@pytest.fixture
def valid_food_data():
    """Valid food data for testing."""
    return {
        "name": "Test Chicken Breast",
        "brand": "Test Farm",
        "description": "Organic chicken breast for testing",
        "serving_size": 100.0,
        "serving_unit": "g",
        "calories_per_serving": 165.0,
        "macros_per_serving": {
            "protein": 31.0,
            "carbs": 0.0,
            "fat": 3.6,
            "fiber": 0.0
        },
        "barcode": "1234567890123"
    }


@pytest.fixture
def valid_ingredient_data():
    """Valid ingredient data for testing."""
    return {
        "name": "Test Spice Mix",
        "quantity": 5.0,
        "unit": "g",
        "calories": 15.0,
        "macros": {
            "protein": 1.0,
            "carbs": 2.0,
            "fat": 0.5,
            "fiber": 0.5
        }
    }


@pytest.fixture
def valid_onboarding_data():
    """Valid onboarding data for testing."""
    return {
        "age": 28,
        "gender": "female",
        "height": 165.0,
        "weight": 60.0,
        "activity_level": "lightly_active",
        "goal": "maintain_weight",
        "goal_weight": 60.0,
        "dietary_preferences": ["vegetarian"],
        "timeline_months": 12
    }


@pytest.fixture
def valid_macros_data():
    """Valid macros data for testing."""
    return {
        "calories": 250.0,
        "macros": {
            "protein": 20.0,
            "carbs": 30.0,
            "fat": 8.0,
            "fiber": 4.0
        },
        "food_id": "test-food-123"
    }


@pytest.fixture
def invalid_data_samples():
    """Collection of invalid data samples for negative testing."""
    return {
        "food_negative_values": {
            "name": "Invalid Food",
            "calories_per_serving": -100.0,  # Negative calories
            "macros_per_serving": {
                "protein": -5.0,  # Negative protein
                "carbs": 20.0,
                "fat": 10.0
            }
        },
        "food_missing_name": {
            "brand": "Test Brand",
            "calories_per_serving": 100.0
            # Missing required 'name' field
        },
        "onboarding_invalid_age": {
            "age": 5,  # Too young
            "gender": "male",
            "height": 180.0,
            "weight": 70.0,
            "activity_level": "moderately_active",
            "goal": "lose_weight"
        },
        "onboarding_invalid_gender": {
            "age": 25,
            "gender": "alien",  # Invalid gender
            "height": 180.0,
            "weight": 70.0,
            "activity_level": "moderately_active",
            "goal": "lose_weight"
        }
    }


# Helper functions
@pytest.fixture
def assert_response_structure():
    """Helper function to assert common response structures."""
    def _assert_structure(response_data: dict, required_fields: list, optional_fields: list = None):
        """Assert that response has required fields and optionally check optional fields."""
        # Check all required fields are present
        for field in required_fields:
            assert field in response_data, f"Required field '{field}' missing from response"
        
        # Check optional fields if they exist
        if optional_fields:
            for field in optional_fields:
                if field in response_data:
                    assert response_data[field] is not None, f"Optional field '{field}' should not be None if present"
    
    return _assert_structure


@pytest.fixture
def assert_pagination_structure():
    """Helper function to assert pagination response structure."""
    def _assert_pagination(response_data: dict):
        """Assert standard pagination structure."""
        required_pagination_fields = ["page", "page_size", "total", "total_pages"]
        for field in required_pagination_fields:
            assert field in response_data, f"Pagination field '{field}' missing from response"
            assert isinstance(response_data[field], int), f"Pagination field '{field}' should be an integer"
            assert response_data[field] >= 0, f"Pagination field '{field}' should be non-negative"
    
    return _assert_pagination


@pytest.fixture
def assert_macros_structure():
    """Helper function to assert macros structure."""
    def _assert_macros(macros_data: dict):
        """Assert standard macros structure."""
        required_macro_fields = ["protein", "carbs", "fat"]
        for field in required_macro_fields:
            assert field in macros_data, f"Macro field '{field}' missing"
            assert isinstance(macros_data[field], (int, float)), f"Macro field '{field}' should be numeric"
            assert macros_data[field] >= 0, f"Macro field '{field}' should be non-negative"
        
        # Fiber is optional but should be non-negative if present
        if "fiber" in macros_data and macros_data["fiber"] is not None:
            assert macros_data["fiber"] >= 0, "Fiber should be non-negative"
    
    return _assert_macros


# Test environment checks
@pytest.fixture(scope="session", autouse=True)
def check_api_availability(base_url: str):
    """Check if the API is available before running tests."""
    try:
        with httpx.Client() as client:
            response = client.get(f"{base_url}/health", timeout=10.0)
            if response.status_code != 200:
                pytest.skip("API server is not available or not healthy")
    except (httpx.ConnectError, httpx.TimeoutException):
        pytest.skip("API server is not reachable")


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Cleanup any test data after each test."""
    # This would be used to clean up test data if we had a real database
    # For now, since we're using placeholder responses, no cleanup is needed
    yield
    # Cleanup code would go here


# Performance testing helpers
@pytest.fixture
def performance_threshold():
    """Define performance thresholds for API endpoints."""
    return {
        "fast_endpoints": 0.5,  # 500ms for simple endpoints
        "medium_endpoints": 2.0,  # 2s for search/calculation endpoints  
        "slow_endpoints": 5.0   # 5s for complex operations
    } 