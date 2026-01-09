"""
Unit tests for update user metrics endpoint and handler.
"""
from unittest.mock import Mock

import pytest

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
from src.app.handlers.command_handlers.update_user_metrics_command_handler import UpdateUserMetricsCommandHandler
from src.infra.database.models.user.profile import UserProfile


class TestUpdateUserMetricsCommand:
    """Test UpdateUserMetricsCommand data class."""
    
    def test_create_command_with_all_fields(self):
        """Test creating command with all metrics."""
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            weight_kg=75.0,
            activity_level="moderately_active",
            body_fat_percent=15.0,
            fitness_goal="cut",
        )

        assert command.user_id == "test_user"
        assert command.weight_kg == 75.0
        assert command.activity_level == "moderately_active"
        assert command.body_fat_percent == 15.0
        assert command.fitness_goal == "cut"

    def test_create_command_with_partial_fields(self):
        """Test creating command with only some metrics."""
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            weight_kg=75.0
        )

        assert command.user_id == "test_user"
        assert command.weight_kg == 75.0
        assert command.activity_level is None
        assert command.body_fat_percent is None
        assert command.fitness_goal is None


@pytest.mark.asyncio
class TestUpdateUserMetricsCommandHandler:
    """Test UpdateUserMetricsCommandHandler."""
    
    async def test_update_weight_only(self):
        """Test updating only weight."""
        # Setup
        mock_db = Mock()
        mock_profile = UserProfile(
            id="profile_1",
            user_id="test_user",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            activity_level="moderate",
            fitness_goal="recomp",
            is_current=False
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            weight_kg=75.0
        )
        
        # Execute
        await handler.handle(command)
        
        # Verify
        assert mock_profile.weight_kg == 75.0
        assert mock_profile.is_current is True
        mock_db.add.assert_called_once_with(mock_profile)
        mock_db.commit.assert_called_once()
    
    async def test_update_activity_level_only(self):
        """Test updating only activity level."""
        # Setup
        mock_db = Mock()
        mock_profile = UserProfile(
            id="profile_1",
            user_id="test_user",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=75.0,
            activity_level="moderate",
            fitness_goal="recomp",
            is_current=False
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            activity_level="very_active"
        )
        
        # Execute
        await handler.handle(command)
        
        # Verify
        assert mock_profile.activity_level == "very_active"
        assert mock_profile.is_current is True

    async def test_update_fitness_goal_unlimited(self):
        """Test updating fitness goal succeeds without cooldown."""
        # Setup
        mock_db = Mock()
        mock_profile = UserProfile(
            id="profile_1",
            user_id="test_user",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=75.0,
            activity_level="moderate",
            fitness_goal="recomp",
            is_current=True,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile

        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            fitness_goal="cut",
        )

        # Execute - should succeed without cooldown check
        await handler.handle(command)

        # Verify
        assert mock_profile.fitness_goal == "cut"
        assert mock_profile.is_current is True
        mock_db.commit.assert_called_once()

    async def test_update_all_metrics_together(self):
        """Test updating all metrics in one call."""
        # Setup
        mock_db = Mock()
        mock_profile = UserProfile(
            id="profile_1",
            user_id="test_user",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            body_fat_percentage=20.0,
            activity_level="moderate",
            fitness_goal="recomp",
            is_current=False,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile

        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            weight_kg=72.5,
            activity_level="very_active",
            body_fat_percent=15.0,
            fitness_goal="cut"
        )
        
        # Execute
        await handler.handle(command)
        
        # Verify all fields updated
        assert mock_profile.weight_kg == 72.5
        assert mock_profile.activity_level == "very_active"
        assert mock_profile.body_fat_percentage == 15.0
        assert mock_profile.fitness_goal == "cut"
        assert mock_profile.is_current is True
    
    async def test_user_not_found(self):
        """Test error when user profile doesn't exist."""
        # Setup
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="nonexistent_user",
            weight_kg=75.0
        )
        
        # Execute & Verify
        with pytest.raises(ResourceNotFoundException):
            await handler.handle(command)
        
        mock_db.rollback.assert_called_once()
    
    async def test_no_metrics_provided(self):
        """Test error when no metrics are provided."""
        # Setup
        mock_db = Mock()
        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(user_id="test_user")
        
        # Execute & Verify
        with pytest.raises(ValidationException) as exc_info:
            await handler.handle(command)
        
        assert "At least one metric must be provided" in str(exc_info.value)
    
    async def test_invalid_weight(self):
        """Test validation for invalid weight."""
        # Setup
        mock_db = Mock()
        mock_profile = UserProfile(
            id="profile_1",
            user_id="test_user",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            activity_level="moderate",
            fitness_goal="recomp"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            weight_kg=-5.0  # Invalid
        )
        
        # Execute & Verify
        with pytest.raises(ValidationException) as exc_info:
            await handler.handle(command)
        
        assert "Weight must be greater than 0" in str(exc_info.value)
        mock_db.rollback.assert_called_once()
    
    async def test_invalid_body_fat(self):
        """Test validation for body fat out of range."""
        # Setup
        mock_db = Mock()
        mock_profile = UserProfile(
            id="profile_1",
            user_id="test_user",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            activity_level="moderate",
            fitness_goal="recomp"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            body_fat_percent=75.0  # Too high
        )
        
        # Execute & Verify
        with pytest.raises(ValidationException) as exc_info:
            await handler.handle(command)
        
        assert "Body fat percentage must be between 0 and 70" in str(exc_info.value)
    
    async def test_invalid_activity_level(self):
        """Test validation for invalid activity level."""
        # Setup
        mock_db = Mock()
        mock_profile = UserProfile(
            id="profile_1",
            user_id="test_user",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            activity_level="moderate",
            fitness_goal="recomp"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            activity_level="super_duper_active"  # Invalid
        )
        
        # Execute & Verify
        with pytest.raises(ValidationException) as exc_info:
            await handler.handle(command)
        
        assert "Activity level must be one of" in str(exc_info.value)
    
    async def test_invalid_fitness_goal(self):
        """Test validation for invalid fitness goal."""
        # Setup
        mock_db = Mock()
        mock_profile = UserProfile(
            id="profile_1",
            user_id="test_user",
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            activity_level="moderate",
            fitness_goal="recomp"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        handler = UpdateUserMetricsCommandHandler(db=mock_db)
        command = UpdateUserMetricsCommand(
            user_id="test_user",
            fitness_goal="super_shredded"  # Invalid
        )
        
        # Execute & Verify
        with pytest.raises(ValidationException) as exc_info:
            await handler.handle(command)
        
        assert "Fitness goal must be one of" in str(exc_info.value)

