"""Movement API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ValidationException, handle_exception
from src.api.schemas.request.movement_requests import LogMovementRequest, UpdateMovementRequest
from src.app.commands.movement import DeleteMovementEntryCommand, LogMovementCommand, UpdateMovementEntryCommand
from src.app.queries.movement import GetDailyMovementQuery, GetMovementCatalogQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/movement", tags=["Movement"])


def _parse_date(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationException("Invalid date format. Use YYYY-MM-DD", "INVALID_DATE") from exc


@router.get("/catalog")
async def get_movement_catalog(
    _: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        return await event_bus.send(GetMovementCatalogQuery())
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def log_movement(
    body: LogMovementRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        command = LogMovementCommand(
            user_id=user_id,
            activity_id=body.activity_id,
            activity_name=body.activity_name,
            duration_min=body.duration_min,
            kcal_burned=body.kcal_burned,
            intensity=body.intensity,
            include_in_balance=body.include_in_balance,
            target_date=_parse_date(body.target_date),
            header_timezone=request.headers.get("X-Timezone"),
        )
        return await event_bus.send(command)
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.get("/daily")
async def get_daily_movement(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    date: Optional[str] = Query(None),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        query = GetDailyMovementQuery(
            user_id=user_id,
            target_date=_parse_date(date),
            header_timezone=request.headers.get("X-Timezone"),
        )
        return await event_bus.send(query)
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.patch("/{entry_id}")
async def update_movement_entry(
    entry_id: str,
    body: UpdateMovementRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        command = UpdateMovementEntryCommand(
            user_id=user_id,
            entry_id=entry_id,
            duration_min=body.duration_min,
            kcal_burned=body.kcal_burned,
            intensity=body.intensity,
            include_in_balance=body.include_in_balance,
        )
        return await event_bus.send(command)
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movement_entry(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        await event_bus.send(DeleteMovementEntryCommand(user_id=user_id, entry_id=entry_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise handle_exception(exc) from exc
