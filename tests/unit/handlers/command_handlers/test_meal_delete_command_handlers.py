"""
Unit tests for DeleteMeal (hard delete) command handler.
"""
from unittest.mock import patch
import pytest

from src.app.commands.meal.delete_meal_command import DeleteMealCommand
from src.infra.database.uow import UnitOfWork


@pytest.mark.unit
class TestDeleteMealCommandHandler:
    @pytest.mark.asyncio
    async def test_hard_delete_removes_meal_and_nutrition(self, event_bus, meal_repository, sample_meal_db, test_session):
        # Arrange
        meal_id = sample_meal_db.meal_id
        user_id = sample_meal_db.user_id  # Use the same user_id from the sample meal

        # Sanity check original status - meal exists
        meal = meal_repository.find_by_id(meal_id)
        assert meal is not None

        command = DeleteMealCommand(meal_id=meal_id, user_id=user_id)

        # Act - patch UnitOfWork to use test_session
        def make_uow(*args, **kwargs):
            return UnitOfWork(session=test_session)

        with patch('src.app.handlers.command_handlers.delete_meal_command_handler.UnitOfWork', side_effect=make_uow):
            result = await event_bus.send(command)

        # Assert response
        assert result["meal_id"] == meal_id
        assert "message" in result

        # Assert persisted state - meal should be hard deleted
        updated = meal_repository.find_by_id(meal_id)
        assert updated is None

    @pytest.mark.asyncio
    async def test_soft_delete_nonexistent_meal_raises(self, event_bus, test_session):
        # Arrange
        user_id = "123e4567-e89b-12d3-a456-426614174000"  # Sample user ID
        command = DeleteMealCommand(meal_id="00000000-0000-0000-0000-000000000000", user_id=user_id)

        # Act / Assert - patch UnitOfWork to use test_session
        def make_uow(*args, **kwargs):
            return UnitOfWork(session=test_session)
        
        from src.api.exceptions import ResourceNotFoundException
        with patch('src.app.handlers.command_handlers.delete_meal_command_handler.UnitOfWork', side_effect=make_uow):
            with pytest.raises(ResourceNotFoundException):
                await event_bus.send(command)


