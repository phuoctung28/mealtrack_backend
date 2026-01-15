"""
Activities API endpoints - Event-driven architecture.
"""

from datetime import datetime

from src.domain.utils.timezone_utils import utc_now
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ValidationException, handle_exception
from src.app.queries.activity import GetDailyActivitiesQuery
from src.infra.event_bus import EventBus

router = APIRouter(
    prefix="/v1/activities",
    tags=["activities"],
)


@router.get("/daily", response_model=None)
async def get_daily_activities(
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

        # Send query
        query = GetDailyActivitiesQuery(user_id=user_id, target_date=target_date)
        activities = await event_bus.send(query)

        return activities

    except Exception as e:
        raise handle_exception(e) from e
