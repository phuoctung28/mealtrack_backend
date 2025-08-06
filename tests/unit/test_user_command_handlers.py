"""
Unit tests for user command handlers.
"""
from datetime import datetime

import pytest

from src.api.exceptions import ValidationException
from src.app.commands.user import SaveUserOnboardingCommand


@pytest.mark.unit
class TestSaveUserOnboardingCommandHandler:
    """Test SaveUserOnboardingCommand handler."""
    
    @pytest.mark.asyncio
    async def test_save_user_onboarding_success(self, event_bus, test_session):
        """Test successful user onboarding save."""
        # Create user first
        from src.infra.database.models.user.user import User
        user = User(
            id="test-user-123",
            firebase_uid="test-firebase-uid-123",
            email="test@example.com",
            username="testuser",
            password_hash="dummy_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id="test-user-123",
            age=30,
            gender="male",
            height_cm=175,
            weight_kg=70,
            activity_level="moderate",
            fitness_goal="maintenance",
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
    
    @pytest.mark.asyncio
    async def test_save_user_onboarding_invalid_age(self, event_bus, test_session):
        """Test onboarding with invalid age."""
        # Create user first
        from src.infra.database.models.user.user import User
        user = User(
            id="test-user-123",
            firebase_uid="test-firebase-uid-123",
            email="test@example.com",
            username="testuser",
            password_hash="dummy_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id="test-user-123",
            age=-5,  # Invalid age
            gender="male",
            height_cm=175,
            weight_kg=70,
            activity_level="moderate",
            fitness_goal="maintenance"
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            await event_bus.send(command)
    
    @pytest.mark.asyncio
    async def test_save_user_onboarding_invalid_weight(self, event_bus, test_session):
        """Test onboarding with invalid weight."""
        # Create user first
        from src.infra.database.models.user.user import User
        user = User(
            id="test-user-123",
            firebase_uid="test-firebase-uid-123",
            email="test@example.com",
            username="testuser",
            password_hash="dummy_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id="test-user-123",
            age=30,
            gender="male",
            height_cm=175,
            weight_kg=0,  # Invalid weight
            activity_level="moderate",
            fitness_goal="maintenance"
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            await event_bus.send(command)
    
    @pytest.mark.asyncio
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
            activity_level="active",  # Different activity
            fitness_goal="cutting",  # Different goal
            dietary_preferences=["vegan"],
            health_conditions=[]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert
        assert result["user_id"] == sample_user_profile.user_id
        assert result["profile_created"] is True
        # Verify profile was updated
        from src.infra.database.models.user.profile import UserProfile
        updated_profile = test_session.query(UserProfile).filter(
            UserProfile.user_id == sample_user_profile.user_id
        ).first()
        assert updated_profile.age == 35
        assert updated_profile.height_cm == 180
        assert updated_profile.weight_kg == 75