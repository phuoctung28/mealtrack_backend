"""Cheat days API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception, ValidationException
from src.app.commands.cheat_day import MarkCheatDayCommand, UnmarkCheatDayCommand
from src.app.queries.cheat_day import GetCheatDaysQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/cheat-days", tags=["Cheat Days"])


@router.post("")
async def mark_cheat_day(
    date_str: str = Query(..., alias="date", description="Date YYYY-MM-DD"),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Mark a date as cheat day. Current day or future only."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        command = MarkCheatDayCommand(user_id=user_id, date=target_date)
        return await event_bus.send(command)
    except ValueError:
        raise ValidationException(
            message="Invalid date format. Use YYYY-MM-DD",
            error_code="INVALID_DATE_FORMAT",
        )
    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/{date_str}")
async def unmark_cheat_day(
    date_str: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Unmark a cheat day."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        command = UnmarkCheatDayCommand(user_id=user_id, date=target_date)
        return await event_bus.send(command)
    except ValueError:
        raise ValidationException(
            message="Invalid date format. Use YYYY-MM-DD",
            error_code="INVALID_DATE_FORMAT",
        )
    except Exception as e:
        raise handle_exception(e) from e


@router.get("")
async def get_cheat_days(
    week_of: Optional[str] = Query(None, description="Date within target week YYYY-MM-DD"),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Get cheat days for a week."""
    try:
        target_date = None
        if week_of:
            target_date = datetime.strptime(week_of, "%Y-%m-%d").date()
        query = GetCheatDaysQuery(user_id=user_id, week_of=target_date)
        return await event_bus.send(query)
    except ValueError:
        raise ValidationException(
            message="Invalid date format. Use YYYY-MM-DD",
            error_code="INVALID_DATE_FORMAT",
        )
    except Exception as e:
        raise handle_exception(e) from e
