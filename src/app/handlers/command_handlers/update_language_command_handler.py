"""Handler for updating user language preference."""

import inspect
import logging
from typing import Any, Dict

from src.app.commands.user.update_language_command import (
    SUPPORTED_LANGUAGES,
    UpdateLanguageCommand,
)
from src.app.events.base import EventHandler, handles
from src.app.services.background_job_scheduler import schedule_background_job
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)

logger = logging.getLogger(__name__)


@handles(UpdateLanguageCommand)
class UpdateLanguageCommandHandler(EventHandler[UpdateLanguageCommand, Dict[str, Any]]):
    """Handler for updating user language preference."""

    def __init__(
        self,
        precompute_service: DailyContextPrecomputeService | None = None,
        task_manager=None,
    ):
        self.precompute_service = precompute_service
        self.task_manager = task_manager

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        if "precompute_service" in kwargs:
            self.precompute_service = kwargs["precompute_service"]
        if "task_manager" in kwargs:
            self.task_manager = kwargs["task_manager"]

    async def handle(self, command: UpdateLanguageCommand) -> Dict[str, Any]:
        """Handle language update command."""
        language = command.language_code.lower().strip()

        if language not in SUPPORTED_LANGUAGES:
            logger.warning(
                f"Invalid language rejected: {language!r} for user {command.user_id}"
            )
            return {"success": False, "error": f"Unsupported language: {language}"}

        async with AsyncUnitOfWork() as uow:
            await uow.users.update_user_language(command.user_id, language)
            await uow.notifications.update_notification_language(
                str(command.user_id), language
            )
            outbox = getattr(uow, "outbox", None)
            if outbox is not None and inspect.iscoroutinefunction(
                getattr(outbox, "enqueue", None)
            ):
                await outbox.enqueue(
                    "notification_reschedule",
                    {"user_id": str(command.user_id), "reason": "language"},
                    event_id=(
                        f"notification-reschedule:language:{command.user_id}:{language}"
                    ),
                    aggregate_type="user",
                    aggregate_id=str(command.user_id),
                )
            await uow.commit()

        self._schedule_notification_reschedule(str(command.user_id), "language")

        logger.info(f"Updated language for user {command.user_id}: {language}")
        return {"success": True, "language_code": language}

    def _schedule_notification_reschedule(self, user_id: str, reason: str) -> None:
        if self.precompute_service is None:
            return
        schedule_background_job(
            self.task_manager,
            f"notifications:reschedule:{user_id}:{reason}",
            self.precompute_service.reschedule_user_notifications(user_id),
            logger=logger,
        )
