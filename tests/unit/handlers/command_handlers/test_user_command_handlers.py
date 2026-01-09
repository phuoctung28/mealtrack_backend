"""
Unit tests for user command handlers.
"""
import uuid
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
        # Create user first with unique IDs
        user_id = str(uuid.uuid4())
        unique_suffix = str(uuid.uuid4())[:8]  # Use only first 8 chars
        firebase_uid = f"test-fb-{unique_suffix}"
        
        from src.infra.database.models.user.user import User
        user = User(
            id=user_id,
            firebase_uid=firebase_uid,
            email=f"test-{unique_suffix}@example.com",
            username=f"user-{unique_suffix}",
            password_hash="dummy_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id=user_id,
            age=30,
            gender="male",
            height_cm=175,
            weight_kg=70,
            activity_level="moderate",
            fitness_goal="recomp",
            dietary_preferences=["vegetarian"],
            pain_points=["diabetes"]
        )
        
        # Act
        result = await event_bus.send(command)
        
        # Assert - SaveUserOnboardingCommand should return None
        assert result is None
        
        # Verify the profile was created/updated in the database
        from src.infra.database.models.user.profile import UserProfile
        saved_profile = test_session.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        
        assert saved_profile is not None
        assert saved_profile.age == 30
        assert saved_profile.gender == "male"
        assert saved_profile.height_cm == 175
        assert saved_profile.weight_kg == 70
        assert saved_profile.activity_level == "moderate"
        assert saved_profile.fitness_goal == "recomp"
    
    @pytest.mark.asyncio
    async def test_save_user_onboarding_invalid_age(self, event_bus, test_session):
        """Test onboarding with invalid age."""
        # Create user first with unique IDs
        user_id = str(uuid.uuid4())
        unique_suffix = str(uuid.uuid4())[:8]  # Use only first 8 chars
        firebase_uid = f"test-fb-{unique_suffix}"
        
        from src.infra.database.models.user.user import User
        user = User(
            id=user_id,
            firebase_uid=firebase_uid,
            email=f"test-{unique_suffix}@example.com",
            username=f"user-{unique_suffix}",
            password_hash="dummy_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id=user_id,
            age=-5,  # Invalid age
            gender="male",
            height_cm=175,
            weight_kg=70,
            activity_level="moderate",
            fitness_goal="maintenance",
            dietary_preferences=[],
            pain_points=[]
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            await event_bus.send(command)
    
    @pytest.mark.asyncio
    async def test_save_user_onboarding_invalid_weight(self, event_bus, test_session):
        """Test onboarding with invalid weight."""
        # Create user first with unique IDs
        user_id = str(uuid.uuid4())
        unique_suffix = str(uuid.uuid4())[:8]  # Use only first 8 chars
        firebase_uid = f"test-fb-{unique_suffix}"
        
        from src.infra.database.models.user.user import User
        user = User(
            id=user_id,
            firebase_uid=firebase_uid,
            email=f"test-{unique_suffix}@example.com",
            username=f"user-{unique_suffix}",
            password_hash="dummy_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Arrange
        command = SaveUserOnboardingCommand(
            user_id=user_id,
            age=30,
            gender="male",
            height_cm=175,
            weight_kg=0,  # Invalid weight
            activity_level="moderate",
            fitness_goal="maintenance",
            dietary_preferences=[],
            pain_points=[]
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
            fitness_goal="cut",  # Different goal
            dietary_preferences=["vegan"],
            pain_points=[]
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