"""
Activities API endpoints - Event-driven architecture.
"""
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ValidationException, handle_exception
from src.app.queries.activity import GetDailyActivitiesQuery
from src.infra.event_bus import EventBus

router = APIRouter(
    prefix="/activities",
    tags=["activities"],
)


@router.get("/daily", response_model=List[Dict])
async def get_daily_activities(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get all activities (meals and workouts) for a specific date.
    
    Returns a unified list of activities including:
    - Meal activities with nutrition data
    - Workout activities (placeholder for future implementation)
    
    Activities are sorted by timestamp in descending order (newest first).
    """
    try:
        # Parse and validate date
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise ValidationException("Invalid date format. Use YYYY-MM-DD")
        else:
            target_date = datetime.now()
        
        # Send query
        query = GetDailyActivitiesQuery(target_date=target_date)
        activities = await event_bus.send(query)
        
        return activities
        
    except Exception as e:
        raise handle_exception(e)