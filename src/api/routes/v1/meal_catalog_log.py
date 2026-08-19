"""Authenticated catalog log and logged-history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.middleware.accept_language import get_request_language
from src.api.middleware.rate_limit import limiter
from src.api.schemas.request.meal_catalog_log_requests import LogCatalogMealRequest
from src.api.schemas.response.meal_catalog_log_responses import (
    LogCatalogMealResponse,
    MealCatalogLoggedListResponse,
)
from src.app.commands.meal_catalog import LogCatalogMealCommand
from src.app.handlers.query_handlers.list_logged_catalog_meals_query_handler import (
    to_logged_item_responses,
)
from src.app.queries.meal_catalog import ListLoggedCatalogMealsQuery
from src.app.queries.user import GetUserTimezoneQuery
from src.domain.utils.timezone_utils import get_zone_info

router = APIRouter(prefix="/v1/meal-catalog", tags=["Meal Catalog"])


@router.get("/logged", response_model=MealCatalogLoggedListResponse)
@limiter.limit("30/minute")
async def list_logged_catalog_meals(
    request: Request,
    limit: int = Query(20, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    event_bus=Depends(get_configured_event_bus),
) -> MealCatalogLoggedListResponse:
    del request
    meals = await event_bus.send(
        ListLoggedCatalogMealsQuery(user_id=user_id, limit=limit)
    )
    return MealCatalogLoggedListResponse(
        items=to_logged_item_responses(meals),
        limit=limit,
    )


@router.post("/{catalog_id}/log", response_model=LogCatalogMealResponse)
@limiter.limit("20/minute")
async def log_catalog_meal(
    request: Request,
    catalog_id: str,
    body: LogCatalogMealRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus=Depends(get_configured_event_bus),
) -> LogCatalogMealResponse:
    timezone = get_zone_info(
        await event_bus.send(
            GetUserTimezoneQuery(
                user_id=user_id,
                header_timezone=request.headers.get("X-Timezone"),
            )
        )
    ).key
    result = await event_bus.send(
        LogCatalogMealCommand(
            user_id=user_id,
            catalog_meal_id=catalog_id,
            meal_date=body.meal_date,
            meal_type=body.meal_type,
            request_id=body.request_id,
            timezone=timezone,
            language=get_request_language(request),
        )
    )
    return LogCatalogMealResponse(
        meal_id=result.meal_id,
        catalog_meal_id=result.catalog_meal_id,
        logged_via=result.logged_via,
        plan_id=result.plan_id,
        slot_id=result.slot_id,
        logged_meal_id=result.logged_meal_id,
        meal_date=result.meal_date,
        meal_type=result.meal_type,
    )
