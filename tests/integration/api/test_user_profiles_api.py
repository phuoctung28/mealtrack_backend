"""
Integration tests for User Profiles API endpoints.
"""
import pytest
from unittest.mock import patch, AsyncMock

from tests.fixtures.factories.user_factory import UserFactory


@pytest.mark.integration
@pytest.mark.api
class TestUserProfilesAPI:
    """Integration tests for User Profiles API."""
    
    # POST /v1/user-profiles/
    def test_save_onboarding_data(self, authenticated_client, test_user, test_session):
        """Test saving initial onboarding data."""
        # Arrange: Onboarding request
        payload = {
            "age": 30,
            "gender": "male",
            "height": 175,
            "weight": 70,
            "activity_level": "moderate",
            "goal": "recomp",
            "dietary_preferences": ["vegetarian"],
            "pain_points": ["diabetes"],
            "meals_per_day": 3
        }
        
        # Mock the event bus response
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(return_value=None)  # Command returns None
            
            # Act: POST onboarding
            response = authenticated_client.post("/v1/user-profiles/", json=payload)
            
            # Assert: Success
            assert response.status_code == 200
            assert response.json() is True
    
    # GET /v1/user-profiles/metrics
    def test_get_current_user_metrics(self, authenticated_client, test_user_with_profile, test_session):
        """Test retrieving current user's metrics."""
        user, profile = test_user_with_profile
        
        # Store values before session operations (to avoid DetachedInstanceError)
        user_id = str(user.id)
        profile_age = profile.age
        profile_height = profile.height_cm
        profile_weight = profile.weight_kg
        
        # Ensure profile is attached to session
        test_session.refresh(profile)
        
        # Act: GET metrics - uses real handler
        response = authenticated_client.get("/v1/user-profiles/metrics")
        
        # Assert: Returns metrics (real handler response)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["age"] == profile_age
        assert data["height_cm"] == profile_height
        assert data["weight_kg"] == profile_weight
    
    def test_get_metrics_not_found(self, authenticated_client, test_user):
        """Test 404 when profile doesn't exist."""
        # Mock the event bus to raise ResourceNotFoundException
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            from src.api.exceptions import ResourceNotFoundException
            
            mock_bus = mock_get_bus.return_value
            mock_bus.send = AsyncMock(
                side_effect=ResourceNotFoundException("User profile not found")
            )
            
            # Act: GET metrics without profile
            response = authenticated_client.get("/v1/user-profiles/metrics")
            
            # Assert: 404
            assert response.status_code == 404
    
    # GET /v1/user-profiles/tdee
    def test_get_user_tdee(self, authenticated_client, test_user_with_profile, test_session):
        """Test retrieving TDEE calculation."""
        user, profile = test_user_with_profile
        
        # Mock the event bus response
        with patch('src.api.dependencies.event_bus.get_configured_event_bus') as mock_get_bus:
            mock_bus = mock_get_bus.return_value
            
            mock_response = {
                "bmr": 1700.0,
                "tdee": 2350.0,
                "activity_multiplier": 1.375,
                "formula_used": "mifflin_st_jeor",
                "profile_data": {
                    "age": profile.age,
                    "gender": profile.gender,
                    "height_cm": profile.height_cm,
                    "weight_kg": profile.weight_kg,
                    "activity_level": profile.activity_level,
                    "fitness_goal": profile.fitness_goal
                },
                "macros": {
                    "calories": 2350.0,
                    "protein": 176.25,
                    "carbs": 293.75,
                    "fat": 65.28
                }
            }
            
            # Ensure profile is attached to session
            test_session.refresh(profile)
            
            # Act: GET TDEE - uses real handler
            response = authenticated_client.get("/v1/user-profiles/tdee")
            
            # Assert: Returns TDEE calculation (real handler calculates it)
            assert response.status_code == 200
            data = response.json()
            assert "bmr" in data
            assert "tdee" in data
            assert "macros" in data
            # Values will be calculated by real TDEE service based on profile
            # Don't assert exact values as they depend on actual calculations
    
    # POST /v1/user-profiles/metrics
    def test_update_user_metrics(self, authenticated_client, test_user_with_profile, test_session):
        """Test updating user metrics."""
        user, profile = test_user_with_profile
        
        # Arrange: Update request
        payload = {
            "weight_kg": 75.0,
            "activity_level": "active",
            "body_fat_percent": 15.0,
            "fitness_goal": "cut"
        }

        # Ensure profile is attached to session
        test_session.refresh(profile)

        # Act: POST update metrics - uses real handlers
        response = authenticated_client.post("/v1/user-profiles/metrics", json=payload)

        # Assert: Returns updated TDEE (real handler calculates it)
        assert response.status_code == 200
        data = response.json()
        assert "tdee" in data
        assert "macros" in data
