"""Hydration API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ValidationException, handle_exception
from src.api.schemas.request.hydration_requests import (
    LogCaloricDrinkRequest,
    LogHydrationRequest,
)
from src.app.commands.hydration import (
    DeleteHydrationEntryCommand,
    LogCaloricDrinkCommand,
    LogHydrationCommand,
)
from src.app.queries.hydration import GetDailyHydrationQuery, GetDrinkCatalogQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/hydration", tags=["Hydration"])


@router.get("/catalog")
async def get_drink_catalog(
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Get the drink catalog with hydration and caloric categories."""
    try:
        query = GetDrinkCatalogQuery()
        return await event_bus.send(query)
    except Exception as e:
        raise handle_exception(e) from e


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def log_hydration(
    body: LogHydrationRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Log a hydration entry for the current user."""
    try:
        target_date = None
        if body.target_date:
            try:
                target_date = datetime.strptime(body.target_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationException("Invalid date format. Use YYYY-MM-DD") from e

        header_timezone = request.headers.get("X-Timezone")
        command = LogHydrationCommand(
            user_id=user_id,
            drink_id=body.drink_id,
            volume_ml=body.volume_ml,
            target_date=target_date,
            header_timezone=header_timezone,
        )
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e


@router.post("/log/drink", status_code=status.HTTP_201_CREATED)
async def log_caloric_drink(
    body: LogCaloricDrinkRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Log a caloric drink entry for the current user."""
    try:
        target_date = None
        if body.target_date:
            try:
                target_date = datetime.strptime(body.target_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationException("Invalid date format. Use YYYY-MM-DD") from e

        header_timezone = request.headers.get("X-Timezone")
        command = LogCaloricDrinkCommand(
            user_id=user_id,
            drink_id=body.drink_id,
            volume_ml=body.volume_ml,
            target_date=target_date,
            header_timezone=header_timezone,
        )
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e


@router.get("/daily")
async def get_daily_hydration(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Get hydration summary for a specific date."""
    try:
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationException("Invalid date format. Use YYYY-MM-DD") from e

        header_timezone = request.headers.get("X-Timezone")
        query = GetDailyHydrationQuery(
            user_id=user_id,
            target_date=target_date,
            header_timezone=header_timezone,
        )
        return await event_bus.send(query)
    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/{entry_id}")
async def delete_hydration_entry(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Delete a hydration entry."""
    try:
        command = DeleteHydrationEntryCommand(user_id=user_id, entry_id=entry_id)
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e
