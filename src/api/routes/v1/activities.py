"""
Activities API endpoints - Event-driven architecture.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ValidationException, handle_exception
from src.api.middleware.accept_language import get_request_language
from src.app.queries.activity import GetDailyActivitiesQuery
from src.domain.utils.timezone_utils import utc_now
from src.infra.event_bus import EventBus

router = APIRouter(
    prefix="/v1/activities",
    tags=["activities"],
)


@router.get("/daily", response_model=None)
async def get_daily_activities(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    date: Optional[str] = Query(
        None, description="Date in YYYY-MM-DD format, defaults to today"
    ),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Get all activities (meals and workouts) for a specific date.

    Returns a unified list of activities including:
    - Meal activities with nutrition data
    - Workout activities (placeholder for future implementation)

    Activities are sorted by timestamp in descending order (newest first).

    Authentication required: User ID is automatically extracted from the Firebase token.
    Language preference is read from Accept-Language header.
    """
    try:
        # Parse and validate date
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError as e:
                raise ValidationException("Invalid date format. Use YYYY-MM-DD") from e
        else:
            target_date = utc_now()

        # Get language from Accept-Language header
        language = get_request_language(request)

        # Send query with language support
        query = GetDailyActivitiesQuery(
            user_id=user_id, target_date=target_date, language=language
        )
        activities = await event_bus.send(query)

        return activities

    except Exception as e:
        raise handle_exception(e) from e
