"""Handler for marking a cheat day."""
import logging
import uuid
from datetime import date
from typing import Dict, Any, Optional

from src.api.exceptions import ValidationException
from src.app.commands.cheat_day import MarkCheatDayCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.cheat_day import CheatDay
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(MarkCheatDayCommand)
class MarkCheatDayCommandHandler(EventHandler[MarkCheatDayCommand, Dict[str, Any]]):

    def __init__(self, uow: Optional[UnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, command: MarkCheatDayCommand) -> Dict[str, Any]:
        uow = self.uow or UnitOfWork()
        with uow:
            try:
                target_date = command.date
                today = date.today()

                if target_date < today:
                    raise ValidationException(
                        message="Cannot mark past dates as cheat days",
                        error_code="PAST_DATE_NOT_ALLOWED",
                    )

                existing = uow.cheat_days.find_by_user_and_date(command.user_id, target_date)
                if existing:
                    raise ValidationException(
                        message=f"Date {target_date} is already marked as cheat day",
                        error_code="ALREADY_MARKED",
                    )

                cheat_day = CheatDay(
                    cheat_day_id=str(uuid.uuid4()),
                    user_id=command.user_id,
                    date=target_date,
                    marked_at=utc_now(),
                )

                uow.cheat_days.add(cheat_day)
                uow.commit()

                return {
                    "cheat_day_id": cheat_day.cheat_day_id,
                    "date": target_date.isoformat(),
                    "message": "Date marked as cheat day",
                }
            except ValidationException:
                uow.rollback()
                raise
            except Exception as e:
                uow.rollback()
                logger.error(f"Error marking cheat day: {e}")
                raise
