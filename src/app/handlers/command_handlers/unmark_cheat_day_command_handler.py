"""Handler for unmarking a cheat day."""
import logging
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.cheat_day import UnmarkCheatDayCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(UnmarkCheatDayCommand)
class UnmarkCheatDayCommandHandler(EventHandler[UnmarkCheatDayCommand, Dict[str, Any]]):

    def __init__(self, uow: Optional[UnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, command: UnmarkCheatDayCommand) -> Dict[str, Any]:
        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            try:
                existing = await uow.cheat_days.find_by_user_and_date(command.user_id, command.date)
                if not existing:
                    raise ResourceNotFoundException(
                        message=f"No cheat day found for date {command.date}",
                        error_code="CHEAT_DAY_NOT_FOUND",
                    )

                await uow.cheat_days.delete(existing.cheat_day_id)
                await uow.commit()

                return {
                    "date": command.date.isoformat(),
                    "message": "Cheat day unmarked",
                }
            except ResourceNotFoundException:
                await uow.rollback()
                raise
            except Exception as e:
                await uow.rollback()
                logger.error(f"Error unmarking cheat day: {e}")
                raise
