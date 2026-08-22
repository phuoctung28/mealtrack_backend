"""
Nutrition API endpoints - bulk data retrieval and presence checks.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ValidationException
from src.api.schemas.response.nutrition_responses import BulkNutritionResponse
from src.app.queries.nutrition import GetNutritionBulkQuery, GetActivitiesPresenceQuery
from src.infra.event_bus import EventBus

router = APIRouter(
    prefix="/v1/nutrition",
    tags=["nutrition"],
)


@router.get("/bulk", response_model=BulkNutritionResponse)
async def get_nutrition_bulk(
    request: Request,
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Get bulk nutrition summaries for a date range.

    Returns date-indexed nutrition data including consumed/target/remaining
    macros for each date, plus the current week's budget summary.

    Max range: 60 days. Typical use: 35 days (5 weeks).

    Authentication required.
    """
    if start > end:
        raise ValidationException(
            message="Start date must be before or equal to end date",
            error_code="INVALID_DATE_RANGE",
        )

    if (end - start).days > 60:
        raise ValidationException(
            message="Date range cannot exceed 60 days",
            error_code="DATE_RANGE_TOO_LARGE",
        )

    header_tz = request.headers.get("X-Timezone")
    query = GetNutritionBulkQuery(
        user_id=user_id,
        start_date=start,
        end_date=end,
        header_timezone=header_tz,
    )
    return await event_bus.send(query)


@router.get("/presence")
async def get_activities_presence(
    request: Request,
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
) -> dict[str, bool]:
    """
    Get presence map for dates with logged meals.

    Returns a simple { "YYYY-MM-DD": boolean } map indicating
    which dates have at least one meal logged.

    Lightweight alternative to bulk endpoint for week navigation dots.

    Max range: 60 days. Typical use: 11 days (visible week + padding).

    Authentication required.
    """
    if start > end:
        raise ValidationException(
            message="Start date must be before or equal to end date",
            error_code="INVALID_DATE_RANGE",
        )

    if (end - start).days > 60:
        raise ValidationException(
            message="Date range cannot exceed 60 days",
            error_code="DATE_RANGE_TOO_LARGE",
        )

    header_tz = request.headers.get("X-Timezone")
    query = GetActivitiesPresenceQuery(
        user_id=user_id,
        start_date=start,
        end_date=end,
        header_timezone=header_tz,
    )
    return await event_bus.send(query)
