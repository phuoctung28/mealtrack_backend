"""
Unit tests for user command handlers.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.app.commands.user import SaveUserOnboardingCommand
from src.domain.model.user.user_profile import UserProfile
from src.api.exceptions import ValidationException


@pytest.mark.unit
class TestSaveUserOnboardingCommandHandler:
    """Test SaveUserOnboardingCommand handler."""
    
    async def test_save_user_onboarding_success(self, event_bus):
        """Test successful user onboarding save."""
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id="test-user-123",
            age=30,
            gender="male",
            height_cm=175,
            weight_kg=70,
            activity_level="moderately_active",
            goal="maintain_weight",
            dietary_preferences=["vegetarian"],
            health_conditions=["diabetes"]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["user_id"] == "test-user-123"
        assert result["profile_created"] is True
        assert "tdee" in result
        assert result["tdee"] > 0
        assert "recommended_calories" in result
        assert "recommended_macros" in result
    
    async def test_save_user_onboarding_invalid_age(self, event_bus):
        """Test onboarding with invalid age."""
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id="test-user-123",
            age=-5,  # Invalid age
            gender="male",
            height_cm=175,
            weight_kg=70,
            activity_level="moderately_active",
            goal="maintain_weight"
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            await event_bus.send(command)
    
    async def test_save_user_onboarding_invalid_weight(self, event_bus):
        """Test onboarding with invalid weight."""
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id="test-user-123",
            age=30,
            gender="male",
            height_cm=175,
            weight_kg=0,  # Invalid weight
            activity_level="moderately_active",
            goal="maintain_weight"
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            await event_bus.send(command)
    
    async def test_save_user_onboarding_updates_existing_profile(
        self, event_bus, test_session, sample_user_profile
    ):
        """Test updating existing user profile."""
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id=sample_user_profile.user_id,
            age=35,  # Different age
            gender="male",
            height_cm=180,  # Different height
            weight_kg=75,  # Different weight
            activity_level="very_active",  # Different activity
            goal="lose_weight",  # Different goal
            dietary_preferences=["vegan"],
            health_conditions=[]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["user_id"] == sample_user_profile.user_id
        assert result["profile_created"] is True
        # Verify profile was updated
        from src.infra.repositories.user_repository import UserRepository
        repo = UserRepository(test_session)
        updated_profile = repo.get_user_profile(sample_user_profile.user_id)
        assert updated_profile.age == 35
        assert updated_profile.height_cm == 180
        assert updated_profile.weight_kg == 75