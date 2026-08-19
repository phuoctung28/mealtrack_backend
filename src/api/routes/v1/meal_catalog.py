"""Authenticated read-only catalog browser endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.api.base_dependencies import get_catalog_meal_browse_service
from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ExternalServiceException, ResourceNotFoundException
from src.api.mappers.catalog_meal_mapper import catalog_meal_browse_response
from src.api.schemas.response.meal_catalog_responses import (
    MealCatalogItemResponse,
    MealCatalogListResponse,
)
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.app.queries.user import GetUserTimezoneQuery
from src.app.services.catalog_meal_browse_ranking import (
    CatalogPopularityUnavailableError,
)
from src.app.services.catalog_meal_browse_service import (
    CatalogFeed,
    CatalogMealBrowseService,
)
from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationCatalogUnavailableError,
)
from src.domain.utils.timezone_utils import get_zone_info

router = APIRouter(prefix="/v1/meal-catalog", tags=["Meal Catalog"])
MealType = Literal["breakfast", "lunch", "dinner", "snack"]


@router.get(
    "",
    response_model=MealCatalogListResponse,
    responses={503: {"description": "Catalog is unavailable or not curated"}},
)
async def list_meal_catalog(
    request: Request,
    feed: CatalogFeed = Query(CatalogFeed.POPULAR),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=160),
    cuisine: str | None = Query(None, max_length=80),
    meal_type: MealType | None = Query(None),
    shuffle_seed: str | None = Query(
        None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    ),
    user_id: str = Depends(get_current_user_id),
    service: CatalogMealBrowseService = Depends(get_catalog_meal_browse_service),
) -> MealCatalogListResponse:
    daily_calories = None
    start_date = None
    timezone = None
    if feed is CatalogFeed.FOR_YOU:
        try:
            event_bus = get_configured_event_bus()
            timezone, start_date, daily_calories = await _personalization_context(
                request,
                user_id=user_id,
                event_bus=event_bus,
            )
        except ExternalServiceException as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=exc.message,
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Catalog personalization context is unavailable",
            ) from exc

    try:
        page = await service.list_meals(
            user_id=user_id,
            feed=feed,
            limit=limit,
            offset=offset,
            query=_clean(q),
            cuisine=_clean(cuisine),
            meal_type=meal_type,
            daily_calories=daily_calories,
            start_date=start_date,
            timezone=timezone,
            shuffle_seed=shuffle_seed,
        )
    except CatalogPopularityUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalog popular feed is not configured",
        ) from exc
    except MealRecommendationCatalogUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.public_detail,
        ) from exc

    return MealCatalogListResponse(
        items=[
            catalog_meal_browse_response(item).model_copy(update={"ingredients": []})
            for item in page.items
        ],
        total=page.total,
        limit=limit,
        offset=offset,
        feed=page.feed.value,
        ranking_source=page.ranking_source,
        fallback=page.fallback,
        allergy_evaluated=page.allergy_evaluated,
    )


@router.get(
    "/{catalog_id}",
    response_model=MealCatalogItemResponse,
    responses={
        404: {"description": "Catalog meal not found"},
        503: {"description": "Catalog is unavailable"},
    },
)
async def get_meal_catalog_detail(
    catalog_id: str,
    user_id: str = Depends(get_current_user_id),
    service: CatalogMealBrowseService = Depends(get_catalog_meal_browse_service),
) -> MealCatalogItemResponse:
    del user_id
    try:
        meal = await service.get_meal(catalog_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog meal not found",
        ) from exc
    except MealRecommendationCatalogUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.public_detail,
        ) from exc
    return catalog_meal_browse_response(meal)


async def _personalization_context(request: Request, *, user_id: str, event_bus):
    """Resolve the same timezone and adjusted target as three-day planning."""
    try:
        timezone = get_zone_info(
            await event_bus.send(
                GetUserTimezoneQuery(
                    user_id=user_id,
                    header_timezone=request.headers.get("X-Timezone"),
                )
            )
        ).key
        target_date = datetime.now(get_zone_info(timezone)).date()
        weekly_budget = await event_bus.send(
            GetWeeklyBudgetQuery(
                user_id=user_id,
                target_date=target_date,
                header_timezone=timezone,
                read_only=True,
            )
        )
        daily_calories = int(round(weekly_budget.get("adjusted_daily_calories") or 0))
        if daily_calories <= 0:
            return timezone, target_date, None
        return timezone, target_date, daily_calories
    except ResourceNotFoundException:
        return None, None, None
    except ExternalServiceException as exc:
        if exc.error_code in {"target_unavailable", "target_service_unavailable"}:
            return None, None, None
        raise
    except Exception as exc:
        raise ExternalServiceException(
            "Catalog personalization context is unavailable",
            "catalog_personalization_unavailable",
        ) from exc


def _clean(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None
