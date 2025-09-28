"""
Unit tests for DeleteMeal (soft delete) command handler.
"""
import pytest

from src.app.commands.meal.delete_meal_command import DeleteMealCommand
from src.domain.model.meal import MealStatus


@pytest.mark.unit
class TestDeleteMealCommandHandler:
    @pytest.mark.asyncio
    async def test_soft_delete_marks_meal_inactive_and_saves(self, event_bus, meal_repository, sample_meal_db):
        # Arrange
        meal_id = sample_meal_db.meal_id

        # Sanity check original status
        meal = meal_repository.find_by_id(meal_id)
        assert meal is not None
        assert meal.status != MealStatus.INACTIVE

        command = DeleteMealCommand(meal_id=meal_id)

        # Act
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
    async def test_soft_delete_nonexistent_meal_raises(self, event_bus):
        # Arrange
        command = DeleteMealCommand(meal_id="00000000-0000-0000-0000-000000000000")

        # Act / Assert
        import pytest
        from src.api.exceptions import ResourceNotFoundException
        with pytest.raises(ResourceNotFoundException):
            await event_bus.send(command)


