"""
Unit tests for DeleteMeal (soft delete) command handler.
"""
from unittest.mock import patch
import pytest

from src.app.commands.meal.delete_meal_command import DeleteMealCommand
from src.domain.model import MealStatus
from src.infra.database.uow import UnitOfWork


@pytest.mark.unit
class TestDeleteMealCommandHandler:
    @pytest.mark.asyncio
    async def test_soft_delete_marks_meal_inactive_and_saves(self, event_bus, meal_repository, sample_meal_db, test_session):
        # Arrange
        meal_id = sample_meal_db.meal_id

        # Sanity check original status
        meal = meal_repository.find_by_id(meal_id)
        assert meal is not None
        assert meal.status != MealStatus.INACTIVE

        command = DeleteMealCommand(meal_id=meal_id)

        # Act - patch UnitOfWork to use test_session
        def make_uow(*args, **kwargs):
            return UnitOfWork(session=test_session)
        
        with patch('src.app.handlers.command_handlers.delete_meal_command_handler.UnitOfWork', side_effect=make_uow):
            result = await event_bus.send(command)

        # Assert response
        assert result["meal_id"] == meal_id
        assert result["status"] == MealStatus.INACTIVE.value
        assert "message" in result

        # Assert persisted state
        updated = meal_repository.find_by_id(meal_id)
        assert updated is not None
        assert updated.status == MealStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_soft_delete_nonexistent_meal_raises(self, event_bus, test_session):
        # Arrange
        command = DeleteMealCommand(meal_id="00000000-0000-0000-0000-000000000000")

        # Act / Assert - patch UnitOfWork to use test_session
        def make_uow(*args, **kwargs):
            return UnitOfWork(session=test_session)
        
        from src.api.exceptions import ResourceNotFoundException
        with patch('src.app.handlers.command_handlers.delete_meal_command_handler.UnitOfWork', side_effect=make_uow):
            with pytest.raises(ResourceNotFoundException):
                await event_bus.send(command)


