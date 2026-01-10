"""
Integration tests for update user metrics API endpoint.
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.api.base_dependencies import get_db
from src.api.main import app
from src.infra.database.models.user import User
from src.infra.database.models.user.profile import UserProfile


@pytest.fixture
def client(test_session):
    """Create a test client with database dependency override."""
    from src.api.dependencies.auth import get_current_user_id
    from src.api.base_dependencies import (
        get_suggestion_orchestration_service,
        get_cache_service,
        get_food_cache_service,
    )
    from src.api.dependencies.event_bus import get_configured_event_bus
    from src.infra.database.config import ScopedSession
    from unittest.mock import Mock, patch
    
    # Reset event bus singleton before setting up client
    import src.api.dependencies.event_bus as event_bus_module
    event_bus_module._configured_event_bus = None
    
    # Create mocks for services
    mock_suggestion_service = Mock()
    mock_cache_service = None  # Disable cache
    mock_food_cache = Mock()
    mock_food_cache.get = Mock(return_value=None)
    mock_food_cache.set = Mock(return_value=True)
    
    # Patch ScopedSession at module level for the entire test
    # This ensures handlers get test_session when they call ScopedSession()
    original_scoped_session_call = getattr(ScopedSession, '__call__', None)
    def mock_scoped_session_call(*args, **kwargs):
        return test_session
    ScopedSession.__call__ = mock_scoped_session_call
    
    def override_get_db():
        try:
            yield test_session
        finally:
            pass  # Session cleanup handled by test_session fixture
    
    def override_get_current_user_id():
        return "test_user_metrics"
    
    def override_get_suggestion_orchestration_service(db=None):
        # Accept db parameter but ignore it, return mock
        return mock_suggestion_service
    
    def override_get_cache_service():
        return mock_cache_service
    
    def override_get_food_cache_service():
        return mock_food_cache
    
    def override_get_configured_event_bus():
        # Patch service getters at module level so get_configured_event_bus() gets mocked versions
        # Reset singleton first
        event_bus_module._configured_event_bus = None
        
        # Create a wrapper that handles both Depends() calls and direct calls
        def mock_get_suggestion_service(*args, **kwargs):
            # Handle both Depends() pattern and direct calls
            return mock_suggestion_service
        
        with patch('src.api.base_dependencies.get_suggestion_orchestration_service', side_effect=mock_get_suggestion_service):
            with patch('src.api.base_dependencies.get_cache_service', return_value=mock_cache_service):
                with patch('src.api.base_dependencies.get_food_cache_service', return_value=mock_food_cache):
                    from src.api.dependencies.event_bus import get_configured_event_bus as real_get_bus
                    return real_get_bus()
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    app.dependency_overrides[get_suggestion_orchestration_service] = override_get_suggestion_orchestration_service
    app.dependency_overrides[get_cache_service] = override_get_cache_service
    app.dependency_overrides[get_food_cache_service] = override_get_food_cache_service
    app.dependency_overrides[get_configured_event_bus] = override_get_configured_event_bus
    
    try:
        client = TestClient(app)
        yield client
    finally:
        # Cleanup
        app.dependency_overrides.clear()
        event_bus_module._configured_event_bus = None
        # Restore original ScopedSession.__call__
        if original_scoped_session_call is not None:
            ScopedSession.__call__ = original_scoped_session_call


@pytest.fixture
def setup_test_user(test_session):
    """Create a test user with profile."""
    # Create user
    user = User(
        id="test_user_metrics",
        firebase_uid="firebase_test_metrics",
        email="test_metrics@example.com",
        username="test_metrics",
        password_hash="hashed",
        is_active=True
    )
    test_session.add(user)
    
    # Create profile
    profile = UserProfile(
        user_id="test_user_metrics",
        age=30,
        gender="male",
        height_cm=175.0,
        weight_kg=70.0,
        body_fat_percentage=20.0,
        activity_level="moderate",
        fitness_goal="recomp",
        meals_per_day=3,
        snacks_per_day=1,
        is_current=True,
        updated_at=datetime.utcnow() - timedelta(days=10)  # Old enough for goal changes
    )
    test_session.add(profile)
    test_session.commit()
    
    yield user, profile
    
    # Cleanup happens automatically via test_session rollback


class TestUpdateMetricsEndpoint:
    """Integration tests for POST /v1/user-profiles/metrics endpoint."""
    
    def test_update_weight_only(self, client, setup_test_user):
        """Test updating only weight returns recalculated TDEE."""
        response = client.post(
            "/v1/user-profiles/metrics",
            json={"weight_kg": 75.0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return TDEE calculation
        assert "bmr" in data
        assert "tdee" in data
        assert "macros" in data
        assert "activity_multiplier" in data
        assert "formula_used" in data
        
        # Check macros structure
        macros = data["macros"]
        assert "calories" in macros
        assert "protein" in macros
        assert "carbs" in macros
        assert "fat" in macros
    
    def test_update_activity_level_only(self, client, setup_test_user):
        """Test updating only activity level."""
        response = client.post(
            "/v1/user-profiles/metrics",
            json={"activity_level": "very_active"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # TDEE should be higher with increased activity
        assert data["tdee"] > 0
        assert data["activity_multiplier"] > 1.5  # very_active multiplier
    
    def test_update_body_fat_only(self, client, setup_test_user):
        """Test updating only body fat percentage."""
        response = client.post(
            "/v1/user-profiles/metrics",
            json={"body_fat_percent": 15.0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use Katch-McArdle formula when body fat is provided
        assert "formula_used" in data
    
    def test_update_fitness_goal_only(self, client, setup_test_user):
        """Test updating only fitness goal."""
        response = client.post(
            "/v1/user-profiles/metrics",
            json={"fitness_goal": "cut"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Goal should affect calorie targets
        assert data["goal"] == "cut"
        assert "macros" in data
    
    def test_update_all_metrics_together(self, client, setup_test_user):
        """Test updating all metrics in one call."""
        response = client.post(
            "/v1/user-profiles/metrics",
            json={
                "weight_kg": 72.5,
                "activity_level": "moderately_active",
                "body_fat_percent": 15.0,
                "fitness_goal": "bulk"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["goal"] == "bulk"
        assert "macros" in data
        assert data["macros"]["calories"] > 0
    
    def test_goal_cooldown_conflict(self, client, setup_test_user):
        """Test goal update within cooldown period returns 409."""
        # First update the goal
        response1 = client.post(
            "/v1/user-profiles/metrics",
            json={"fitness_goal": "cut"}
        )
        assert response1.status_code == 200
        
        # Immediately try to change it again (should fail)
        response2 = client.post(
            "/v1/user-profiles/metrics",
            json={"fitness_goal": "bulk"}
        )
        
        assert response2.status_code == 409
        data = response2.json()
        
        # Should include cooldown information
        assert "detail" in data
        assert "cooldown_until" in str(data)
    
    def test_goal_cooldown_override(self, client, setup_test_user):
        """Test goal update with override bypasses cooldown."""
        # First update the goal
        response1 = client.post(
            "/v1/user-profiles/metrics",
            json={"fitness_goal": "cut"}
        )
        assert response1.status_code == 200
        
        # Immediately change it again with override
        response2 = client.post(
            "/v1/user-profiles/metrics",
            json={"fitness_goal": "bulk", "override": True}
        )
        
        assert response2.status_code == 200
        data = response2.json()
        assert data["goal"] == "bulk"
    
    def test_invalid_weight(self, client, setup_test_user):
        """Test validation error for invalid weight."""
        response = client.post(
            "/v1/user-profiles/metrics",
            json={"weight_kg": -5.0}
        )
        
        assert response.status_code == 422  # Pydantic validation
    
    def test_invalid_body_fat(self, client, setup_test_user):
        """Test validation error for body fat out of range."""
        response = client.post(
            "/v1/user-profiles/metrics",
            json={"body_fat_percent": 75.0}
        )
        
        assert response.status_code == 422  # Pydantic validation
    
    def test_empty_request(self, client, setup_test_user):
        """Test error when no metrics provided."""
        response = client.post(
            "/v1/user-profiles/metrics",
            json={}
        )
        
        assert response.status_code in [400, 422]
    
    def test_nonexistent_user(self, client, test_session):
        """Test error when user doesn't exist."""
        from src.api.dependencies.auth import get_current_user_id
        
        # Override to return non-existent user
        def override_get_nonexistent_user():
            return "nonexistent_user"
        
        app.dependency_overrides[get_current_user_id] = override_get_nonexistent_user
        
        response = client.post(
            "/v1/user-profiles/metrics",
            json={"weight_kg": 75.0}
        )
        
        assert response.status_code == 404
    
    def test_metrics_update_affects_subsequent_tdee_query(self, client, setup_test_user):
        """Test that metrics update affects subsequent TDEE queries."""
        # Update metrics
        update_response = client.post(
            "/v1/user-profiles/metrics",
            json={"weight_kg": 80.0, "activity_level": "very_active"}
        )
        assert update_response.status_code == 200
        updated_tdee = update_response.json()["tdee"]
        
        # Query TDEE
        query_response = client.get("/v1/user-profiles/tdee")
        assert query_response.status_code == 200
        queried_tdee = query_response.json()["tdee"]
        
        # Should match
        assert abs(updated_tdee - queried_tdee) < 1.0  # Allow small rounding difference

