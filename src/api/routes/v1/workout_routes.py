"""Workout logging API endpoints."""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception, ValidationException
from src.api.schemas.request.workout_requests import LogWorkoutRequest
from src.app.commands.workout.log_workout_command import LogWorkoutCommand
from src.app.commands.workout.delete_workout_command import DeleteWorkoutCommand
from src.app.queries.workout.get_workouts_for_date_query import GetWorkoutsForDateQuery
from src.infra.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/workouts", tags=["Workouts"])


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def log_workout(
    payload: LogWorkoutRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Log a workout session.

    Computes estimated_burn_kcal via MET formula when user weight is available;
    returns null otherwise.
    """
    try:
        command = LogWorkoutCommand(
            user_id=user_id,
            workout_type=payload.workout_type,
            intensity=payload.intensity,
            duration_minutes=payload.duration_minutes,
            logged_at=payload.logged_at,
            notes=payload.notes,
        )
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e


@router.get("")
async def get_workouts_for_date(
    request: Request,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Get all workout logs for the authenticated user on a specific date.

    Timezone is resolved from the user's profile (X-Timezone header as fallback).
    """
    try:
        target_date: date
        if date:
            try:
                from datetime import date as date_type
                target_date = date_type.fromisoformat(date)
            except ValueError as exc:
                raise ValidationException(
                    message="Invalid date format. Use YYYY-MM-DD.",
                    error_code="INVALID_DATE_FORMAT",
                    details={"date": date},
                ) from exc
        else:
            from datetime import date as date_type
            target_date = date_type.today()

        header_tz = request.headers.get("X-Timezone")
        query = GetWorkoutsForDateQuery(
            user_id=user_id,
            target_date=target_date,
            header_timezone=header_tz,
        )
        return await event_bus.send(query)
    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/{workout_log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_log_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Delete a workout log entry. Returns 403 if the log belongs to another user."""
    try:
        command = DeleteWorkoutCommand(
            workout_log_id=workout_log_id,
            user_id=user_id,
        )
        await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e
