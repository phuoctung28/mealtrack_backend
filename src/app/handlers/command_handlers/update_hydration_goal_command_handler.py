"""Handler for updating a user's daily hydration goal."""

import logging
from typing import Any, Dict

from src.api.exceptions import ValidationException
from src.app.commands.hydration.update_hydration_goal_command import (
    UpdateHydrationGoalCommand,
)
from src.app.events.base import EventHandler, handles
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)

_GOAL_MIN_ML = 500
_GOAL_MAX_ML = 4000


@handles(UpdateHydrationGoalCommand)
class UpdateHydrationGoalCommandHandler(
    EventHandler[UpdateHydrationGoalCommand, Dict[str, Any]]
):
    """Updates users.hydration_goal_ml. Enforces 500–4000 ml bounds."""

    async def handle(self, command: UpdateHydrationGoalCommand) -> Dict[str, Any]:
        if not (_GOAL_MIN_ML <= command.goal_ml <= _GOAL_MAX_ML):
            raise ValidationException(
                message=(
                    f"hydration_goal_ml must be between {_GOAL_MIN_ML} and "
                    f"{_GOAL_MAX_ML} ml, got {command.goal_ml}"
                ),
                error_code="INVALID_HYDRATION_GOAL",
                details={"goal_ml": command.goal_ml, "min": _GOAL_MIN_ML, "max": _GOAL_MAX_ML},
            )

        async with AsyncUnitOfWork() as uow:
            new_goal = await uow.hydration.update_user_hydration_goal(
                command.user_id, command.goal_ml
            )
            await uow.commit()

        return {"goal_ml": new_goal}
