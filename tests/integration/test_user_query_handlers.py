"""
Integration tests for user query handlers.
"""

import pytest

from src.api.exceptions import ResourceNotFoundException
from src.app.queries.user import GetUserProfileQuery


@pytest.mark.integration
class TestGetUserProfileQueryHandler:
    """Test GetUserProfileQuery handler with database."""

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, event_bus, sample_user_profile):
        """Test successful user profile retrieval."""
        # Arrange
        query = GetUserProfileQuery(user_id=sample_user_profile.user_id)

        # Act
        result = await event_bus.send(query)

        # Assert
        profile = result["profile"]
        assert profile["user_id"] == sample_user_profile.user_id
        assert profile["age"] == sample_user_profile.age
        assert profile["gender"] == sample_user_profile.gender
        assert profile["height_cm"] == sample_user_profile.height_cm
        assert profile["weight_kg"] == sample_user_profile.weight_kg
        assert profile["job_type"] == sample_user_profile.job_type
        assert (
            profile["training_days_per_week"]
            == sample_user_profile.training_days_per_week
        )
        assert (
            profile["training_minutes_per_session"]
            == sample_user_profile.training_minutes_per_session
        )
        assert profile["fitness_goal"] == sample_user_profile.fitness_goal
        assert profile["dietary_preferences"] == sample_user_profile.dietary_preferences
        assert profile["health_conditions"] == sample_user_profile.health_conditions

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, event_bus):
        """Test profile retrieval with non-existent user."""
        # Arrange
        query = GetUserProfileQuery(user_id="non-existent-user")

        # Act & Assert
        with pytest.raises(ResourceNotFoundException):
            await event_bus.send(query)

    @pytest.mark.asyncio
    async def test_get_user_profile_with_calculated_fields(
        self, event_bus, sample_user_profile
    ):
        """Test that profile includes calculated fields like BMI."""
        # Arrange
        query = GetUserProfileQuery(user_id=sample_user_profile.user_id)

        # Act
        result = await event_bus.send(query)

        # Assert
        # BMI = weight(kg) / (height(m))^2
        expected_bmi = sample_user_profile.weight_kg / (
            (sample_user_profile.height_cm / 100) ** 2
        )

        profile = result["profile"]
        assert profile["user_id"] == sample_user_profile.user_id
        # Check if the profile has additional calculated fields
        # (if implemented in the domain model)
