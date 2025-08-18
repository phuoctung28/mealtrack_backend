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
            id="550e8400-e29b-41d4-a716-446655440001",
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
            user_id="550e8400-e29b-41d4-a716-446655440001",
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
        
        # Assert - SaveUserOnboardingCommand should return None
        assert result is None
        
        # Verify the profile was created/updated in the database
        from src.infra.database.models.user.profile import UserProfile
        saved_profile = test_session.query(UserProfile).filter(
            UserProfile.user_id == "550e8400-e29b-41d4-a716-446655440001"
        ).first()
        
        assert saved_profile is not None
        assert saved_profile.age == 30
        assert saved_profile.gender == "male"
        assert saved_profile.height_cm == 175
        assert saved_profile.weight_kg == 70
        assert saved_profile.activity_level == "moderate"
        assert saved_profile.fitness_goal == "maintenance"
    
    @pytest.mark.asyncio
    async def test_save_user_onboarding_invalid_age(self, event_bus, test_session):
        """Test onboarding with invalid age."""
        # Create user first
        from src.infra.database.models.user.user import User
        user = User(
            id="550e8400-e29b-41d4-a716-446655440001",
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
            user_id="550e8400-e29b-41d4-a716-446655440001",
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
            id="550e8400-e29b-41d4-a716-446655440001",
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
            user_id="550e8400-e29b-41d4-a716-446655440001",
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
        
        # Assert - SaveUserOnboardingCommand should return None
        assert result is None
        # Verify profile was updated
        from src.infra.database.models.user.profile import UserProfile
        updated_profile = test_session.query(UserProfile).filter(
            UserProfile.user_id == sample_user_profile.user_id
        ).first()
        assert updated_profile.age == 35
        assert updated_profile.height_cm == 180
        assert updated_profile.weight_kg == 75