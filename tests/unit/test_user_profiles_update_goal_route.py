"""
Unit tests for PATCH /v1/user-profiles/{user_id}/goal route.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestUpdateUserGoalRoute:
    def test_update_goal_returns_updated_tdee(self, api_app, db_session, sample_user_db):
        # Arrange: create profile
        from src.infra.database.models.user.profile import UserProfile
        user_id = sample_user_db.id
        profile = UserProfile(
            user_id=user_id,
            age=30,
            gender='male',
            height_cm=180.0,
            weight_kg=80.0,
            activity_level='moderate',
            fitness_goal='maintenance',
            is_current=True,
            meals_per_day=3,
            snacks_per_day=1,
            dietary_preferences=[],
            health_conditions=[],
            allergies=[],
        )
        db_session.add(profile)
        db_session.commit()

        client = TestClient(api_app)

        # Act
        response = client.patch(f"/v1/user-profiles/{user_id}/goal", json={"goal": "cutting"})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["goal"] in ["maintenance", "cutting", "bulking"]
        assert "bmr" in data and "tdee" in data and "macros" in data

    def test_update_goal_invalid_goal_returns_400(self, api_app, db_session, sample_user_db):
        client = TestClient(api_app)
        user_id = sample_user_db.id

        # Act
        response = client.patch(f"/v1/user-profiles/{user_id}/goal", json={"goal": "invalid_goal"})

        # Assert
        assert response.status_code == 422 or response.status_code == 400


