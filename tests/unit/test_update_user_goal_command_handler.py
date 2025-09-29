"""
Unit tests for UpdateUserGoalCommandHandler.
"""
import pytest

from src.app.commands.user.update_user_goal_command import UpdateUserGoalCommand
from src.infra.database.models.user.profile import UserProfile


@pytest.mark.unit
class TestUpdateUserGoalCommandHandler:
    @pytest.mark.asyncio
    async def test_update_goal_updates_profile_and_commits(self, event_bus, db_session, sample_user_db):
        # Arrange: create a current profile
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

        # Act
        command = UpdateUserGoalCommand(user_id=user_id, goal='bulking')
        await event_bus.send(command)

        # Assert
        updated = db_session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        assert updated is not None
        assert updated.fitness_goal == 'bulking'

    @pytest.mark.asyncio
    async def test_update_goal_nonexistent_profile_raises(self, event_bus):
        # Arrange
        command = UpdateUserGoalCommand(user_id='00000000-0000-0000-0000-000000000000', goal='cutting')

        # Act / Assert
        import pytest
        from src.api.exceptions import ResourceNotFoundException
        with pytest.raises(ResourceNotFoundException):
            await event_bus.send(command)


