"""Weight entries API endpoints."""

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request.weight_entry_requests import (
    AddWeightEntryRequest,
    SyncWeightEntriesRequest,
)
from src.app.commands.weight import (
    AddWeightEntryCommand,
    DeleteWeightEntryCommand,
    SyncWeightEntriesCommand,
)
from src.app.commands.weight.sync_weight_entries_command import WeightEntryData
from src.app.queries.weight import GetWeightEntriesQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/weight-entries", tags=["Weight Entries"])


@router.get("")
async def get_weight_entries(
    limit: int = 100,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Get user's weight entry history."""
    try:
        query = GetWeightEntriesQuery(user_id=user_id, limit=limit, offset=offset)
        return await event_bus.send(query)
    except Exception as e:
        raise handle_exception(e) from e


@router.post("")
async def add_weight_entry(
    request: AddWeightEntryRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Add a single weight entry."""
    try:
        command = AddWeightEntryCommand(
            user_id=user_id,
            weight_kg=request.weight_kg,
            recorded_at=request.recorded_at,
        )
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/{entry_id}")
async def delete_weight_entry(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Delete a weight entry."""
    try:
        command = DeleteWeightEntryCommand(user_id=user_id, entry_id=entry_id)
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e


@router.post("/sync")
async def sync_weight_entries(
    request: SyncWeightEntriesRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Bulk sync weight entries from mobile."""
    try:
        entries = [
            WeightEntryData(weight_kg=e.weight_kg, recorded_at=e.recorded_at)
            for e in request.entries
        ]
        command = SyncWeightEntriesCommand(user_id=user_id, entries=entries)
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e
