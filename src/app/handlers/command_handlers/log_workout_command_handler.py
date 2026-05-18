"""Handler for logging a workout session with MET-based calorie estimation."""

import logging
from typing import Any, Dict

from src.app.commands.workout.log_workout_command import LogWorkoutCommand
from src.app.events.base import EventHandler, handles
from src.domain.constants.met_table import MET_TABLE, estimate_burn
from src.domain.model.workout.workout_log import WorkoutLog
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(LogWorkoutCommand)
class LogWorkoutCommandHandler(EventHandler[LogWorkoutCommand, Dict[str, Any]]):
    """Creates a workout log and computes estimated calorie burn via MET formula."""

    async def handle(self, command: LogWorkoutCommand) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            user = await uow.users.find_by_id(command.user_id)
            weight_kg: float | None = None
            if user and user.current_profile:
                weight_kg = user.current_profile.weight_kg

            met = MET_TABLE.get((command.workout_type, command.intensity))
            if met is None:
                # Fallback: use OTHER/MODERATE as a safe default
                from src.domain.model.workout.workout_log import Intensity, WorkoutType
                met = MET_TABLE[(WorkoutType.OTHER, Intensity.MODERATE)]

            burn = estimate_burn(met, weight_kg, command.duration_minutes)

            log = WorkoutLog.create_new(
                user_id=command.user_id,
                workout_type=command.workout_type,
                intensity=command.intensity,
                duration_minutes=command.duration_minutes,
                logged_at=command.logged_at,
                met_value=met,
                weight_kg_snapshot=weight_kg,
                estimated_burn_kcal=burn,
                notes=command.notes,
            )
            saved = await uow.workouts.save(log)
            await uow.commit()

            return {
                "id": saved.workout_log_id,
                "workout_type": saved.workout_type.value,
                "intensity": saved.intensity.value,
                "duration_minutes": saved.duration_minutes,
                "estimated_burn_kcal": saved.estimated_burn_kcal,
                "logged_at": saved.logged_at.isoformat() if saved.logged_at else None,
                "notes": saved.notes,
                "created_at": saved.created_at.isoformat() if saved.created_at else None,
            }
