"""Saved suggestions API endpoints — bookmark/unbookmark meal suggestions."""
from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.app.commands.saved_suggestion import (
    SaveSuggestionCommand,
    DeleteSavedSuggestionCommand,
)
from src.app.queries.saved_suggestion import GetSavedSuggestionsQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/saved-suggestions", tags=["Saved Suggestions"])


class SaveSuggestionRequest(BaseModel):
    """Validated request body for saving a suggestion."""
    suggestion_id: str = Field(..., min_length=1, max_length=64)
    meal_type: str = Field(..., min_length=1, max_length=20)
    portion_multiplier: int = Field(default=1, ge=1)
    suggestion_data: Dict[str, Any] = Field(...)


@router.get("")
async def list_saved_suggestions(
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """List all saved suggestions for the current user (newest first)."""
    try:
        query = GetSavedSuggestionsQuery(user_id=user_id)
        return await event_bus.send(query)
    except Exception as e:
        raise handle_exception(e) from e


@router.post("")
async def save_suggestion(
    request: SaveSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Save a meal suggestion. Idempotent — returns existing if already saved."""
    try:
        command = SaveSuggestionCommand(
            user_id=user_id,
            suggestion_id=request.suggestion_id,
            meal_type=request.meal_type,
            portion_multiplier=request.portion_multiplier,
            suggestion_data=request.suggestion_data,
        )
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/{suggestion_id}")
async def delete_saved_suggestion(
    suggestion_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Remove a saved suggestion."""
    try:
        command = DeleteSavedSuggestionCommand(
            user_id=user_id,
            suggestion_id=suggestion_id,
        )
        return await event_bus.send(command)
    except Exception as e:
        raise handle_exception(e) from e
