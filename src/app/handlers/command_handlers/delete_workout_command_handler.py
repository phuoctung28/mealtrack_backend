"""Handler for deleting a workout log entry with ownership check."""

import logging
from typing import Any, Dict

from src.api.exceptions import AuthorizationException, ResourceNotFoundException
from src.app.commands.workout.delete_workout_command import DeleteWorkoutCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(DeleteWorkoutCommand)
class DeleteWorkoutCommandHandler(EventHandler[DeleteWorkoutCommand, Dict[str, Any]]):
    """Deletes a workout log after verifying the caller owns the record."""

    async def handle(self, command: DeleteWorkoutCommand) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            # Verify existence before attempting delete (gives 404 vs 403 distinction)
            existing = await uow.workouts.find_by_id(command.workout_log_id)
            if existing is None:
                raise ResourceNotFoundException(
                    message=f"Workout log {command.workout_log_id} not found",
                    error_code="WORKOUT_LOG_NOT_FOUND",
                )

            if existing.user_id != command.user_id:
                raise AuthorizationException(
                    message="You do not have permission to delete this workout log",
                    error_code="WORKOUT_LOG_FORBIDDEN",
                )

            deleted = await uow.workouts.delete(command.workout_log_id, command.user_id)
            if not deleted:
                raise ResourceNotFoundException(
                    message=f"Workout log {command.workout_log_id} not found",
                    error_code="WORKOUT_LOG_NOT_FOUND",
                )
            await uow.commit()

        return {"deleted": True}
