"""
Integration tests for update user metrics API endpoint.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.api.main import app
from src.infra.database.models.user import User
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.config import engine
from sqlalchemy.orm import sessionmaker


client = TestClient(app)
SessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def setup_test_user():
    """Create a test user with profile."""
    session = SessionLocal()
    try:
        # Create user
        user = User(
            id="test_user_metrics",
            firebase_uid="firebase_test_metrics",
            email="test_metrics@example.com",
            username="test_metrics",
            password_hash="hashed",
            is_active=True
        )
        session.add(user)
        
        # Create profile
        profile = UserProfile(
            user_id="test_user_metrics",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            body_fat_percentage=20.0,
            activity_level="moderate",
            fitness_goal="maintenance",
            meals_per_day=3,
            snacks_per_day=1,
            is_current=True,
            updated_at=datetime.utcnow() - timedelta(days=10)  # Old enough for goal changes
        )
        session.add(profile)
        session.commit()
        
        yield user, profile
        
    finally:
        # Cleanup
        session.query(UserProfile).filter(UserProfile.user_id == "test_user_metrics").delete()
        session.query(User).filter(User.id == "test_user_metrics").delete()
        session.commit()
        session.close()


class TestUpdateMetricsEndpoint:
    """Integration tests for POST /v1/user-profiles/{user_id}/metrics endpoint."""
    
    def test_update_weight_only(self, setup_test_user):
        """Test updating only weight returns recalculated TDEE."""
        response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
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
    
    def test_update_activity_level_only(self, setup_test_user):
        """Test updating only activity level."""
        response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"activity_level": "very_active"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # TDEE should be higher with increased activity
        assert data["tdee"] > 0
        assert data["activity_multiplier"] > 1.5  # very_active multiplier
    
    def test_update_body_fat_only(self, setup_test_user):
        """Test updating only body fat percentage."""
        response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"body_fat_percent": 15.0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use Katch-McArdle formula when body fat is provided
        assert "formula_used" in data
    
    def test_update_fitness_goal_only(self, setup_test_user):
        """Test updating only fitness goal."""
        response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"fitness_goal": "cutting"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Goal should affect calorie targets
        assert data["goal"] == "cutting"
        assert "macros" in data
    
    def test_update_all_metrics_together(self, setup_test_user):
        """Test updating all metrics in one call."""
        response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={
                "weight_kg": 72.5,
                "activity_level": "moderately_active",
                "body_fat_percent": 15.0,
                "fitness_goal": "bulking"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["goal"] == "bulking"
        assert "macros" in data
        assert data["macros"]["calories"] > 0
    
    def test_goal_cooldown_conflict(self, setup_test_user):
        """Test goal update within cooldown period returns 409."""
        # First update the goal
        response1 = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"fitness_goal": "cutting"}
        )
        assert response1.status_code == 200
        
        # Immediately try to change it again (should fail)
        response2 = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"fitness_goal": "bulking"}
        )
        
        assert response2.status_code == 409
        data = response2.json()
        
        # Should include cooldown information
        assert "detail" in data
        assert "cooldown_until" in str(data)
    
    def test_goal_cooldown_override(self, setup_test_user):
        """Test goal update with override bypasses cooldown."""
        # First update the goal
        response1 = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"fitness_goal": "cutting"}
        )
        assert response1.status_code == 200
        
        # Immediately change it again with override
        response2 = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"fitness_goal": "bulking", "override": True}
        )
        
        assert response2.status_code == 200
        data = response2.json()
        assert data["goal"] == "bulking"
    
    def test_invalid_weight(self, setup_test_user):
        """Test validation error for invalid weight."""
        response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"weight_kg": -5.0}
        )
        
        assert response.status_code == 422  # Pydantic validation
    
    def test_invalid_body_fat(self, setup_test_user):
        """Test validation error for body fat out of range."""
        response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"body_fat_percent": 75.0}
        )
        
        assert response.status_code == 422  # Pydantic validation
    
    def test_empty_request(self, setup_test_user):
        """Test error when no metrics provided."""
        response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={}
        )
        
        assert response.status_code in [400, 422]
    
    def test_nonexistent_user(self):
        """Test error when user doesn't exist."""
        response = client.post(
            "/v1/user-profiles/nonexistent_user/metrics",
            json={"weight_kg": 75.0}
        )
        
        assert response.status_code == 404
    
    def test_metrics_update_affects_subsequent_tdee_query(self, setup_test_user):
        """Test that metrics update affects subsequent TDEE queries."""
        # Update metrics
        update_response = client.post(
            "/v1/user-profiles/test_user_metrics/metrics",
            json={"weight_kg": 80.0, "activity_level": "very_active"}
        )
        assert update_response.status_code == 200
        updated_tdee = update_response.json()["tdee"]
        
        # Query TDEE
        query_response = client.get("/v1/user-profiles/test_user_metrics/tdee")
        assert query_response.status_code == 200
        queried_tdee = query_response.json()["tdee"]
        
        # Should match
        assert abs(updated_tdee - queried_tdee) < 1.0  # Allow small rounding difference

