"""Hydration logging API endpoints, including hydration goal update."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception, ValidationException
from src.api.schemas.request.hydration_requests import (
    LogHydrationRequest,
    UpdateHydrationGoalRequest,
)
from src.app.commands.hydration.log_hydration_command import LogHydrationCommand
from src.app.commands.hydration.delete_hydration_command import DeleteHydrationCommand
from src.app.commands.hydration.update_hydration_goal_command import (
    UpdateHydrationGoalCommand,
)
from src.app.queries.hydration.get_hydration_for_date_query import (
    GetHydrationForDateQuery,
)
from src.infra.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Hydration"])


@router.post("/v1/hydration/log", status_code=status.HTTP_201_CREATED)
async def log_hydration(
    payload: LogHydrationRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Log a hydration entry. volume_ml must be 1–2000."""
    try:
        command = LogHydrationCommand(
            user_id=user_id,
            drink_type=payload.drink_type,
            volume_ml=payload.volume_ml,
            logged_at=payload.logged_at,
        )
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e


@router.get("/v1/hydration")
async def get_hydration_for_date(
    request: Request,
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Get hydration entries for the authenticated user on a specific date.

    Returns entries, goal_ml and total_ml.
    Timezone is resolved from the user's profile (X-Timezone header as fallback).
    """
    try:
        from datetime import date as date_type

        if date:
            try:
                target_date = date_type.fromisoformat(date)
            except ValueError as exc:
                raise ValidationException(
                    message="Invalid date format. Use YYYY-MM-DD.",
                    error_code="INVALID_DATE_FORMAT",
                    details={"date": date},
                ) from exc
        else:
            target_date = date_type.today()

        header_tz = request.headers.get("X-Timezone")
        query = GetHydrationForDateQuery(
            user_id=user_id,
            target_date=target_date,
            header_timezone=header_tz,
        )
        return await event_bus.send(query)
    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/v1/hydration/{hydration_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hydration(
    hydration_entry_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Delete a hydration entry. Returns 403 if the entry belongs to another user."""
    try:
        command = DeleteHydrationCommand(
            hydration_entry_id=hydration_entry_id,
            user_id=user_id,
        )
        await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e


@router.patch("/v1/users/me/hydration-goal")
async def update_hydration_goal(
    payload: UpdateHydrationGoalRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Update the authenticated user's daily hydration goal (500–4000 ml)."""
    try:
        command = UpdateHydrationGoalCommand(
            user_id=user_id,
            goal_ml=payload.goal_ml,
        )
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e
