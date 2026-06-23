"""Progress API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Request

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.schemas.progress_schemas import JourneyProgressResponse
from src.app.queries.progress import GetJourneyProgressQuery

router = APIRouter(prefix="/v1/progress", tags=["Progress"])


@router.get("/journey", response_model=JourneyProgressResponse)
async def get_journey_progress(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    event_bus: Any = Depends(get_configured_event_bus),
):
    """Get the current action-based journey progress snapshot."""
    query = GetJourneyProgressQuery(
        user_id=user_id,
        header_timezone=request.headers.get("X-Timezone"),
    )
    return await event_bus.send(query)
