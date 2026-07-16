"""Durable catalog-backed meal recommendation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.middleware.rate_limit import limiter
from src.api.schemas.response.meal_recommendation_responses import (
    MealRecommendationAlternativeResponse,
    MealRecommendationPlanResponse,
    MealRecommendationSlotResponse,
)
from src.app.commands.meal_recommendation import (
    CreateThreeDayMealRecommendationCommand,
    LogRecommendedMealCommand,
    SwapMealRecommendationSlotCommand,
)
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.app.queries.meal_recommendation import GetMealRecommendationPlanQuery
from src.app.queries.user import GetUserTimezoneQuery
from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationCreationError,
)
from src.domain.model.meal_recommendation import PersistedMealRecommendationPlan
from src.domain.utils.timezone_utils import get_zone_info

router = APIRouter(prefix="/v1/meal-recommendations", tags=["Meal Recommendations"])


class SwapMealRecommendationSlotRequest(BaseModel):
    request_id: str = Field(..., min_length=1, max_length=160)
    expected_version: int = Field(..., ge=1)
    alternative_recipe_version_id: str | None = None
    reason: Literal["user_requested", "alternative_selected"] = "user_requested"

    @field_validator("request_id")
    @classmethod
    def normalize_request_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("request_id is required")
        return normalized


class LogRecommendedMealRequest(BaseModel):
    request_id: str = Field(..., min_length=1, max_length=160)

    @field_validator("request_id")
    @classmethod
    def normalize_request_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("request_id is required")
        return normalized


@router.post("/three-day", response_model=MealRecommendationPlanResponse)
@limiter.limit("5/minute")
async def create_three_day_recommendations(
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user_id: str = Depends(get_current_user_id),
    event_bus=Depends(get_configured_event_bus),
) -> MealRecommendationPlanResponse:
    """Create or replay a durable three-day catalog recommendation plan."""

    normalized_idempotency_key = idempotency_key.strip()
    if not normalized_idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key is required",
        )
    if len(normalized_idempotency_key) > 160:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must be 160 characters or fewer",
        )
    header_timezone = request.headers.get("X-Timezone")
    timezone = get_zone_info(
        await event_bus.send(
            GetUserTimezoneQuery(user_id=user_id, header_timezone=header_timezone)
        )
    ).key
    start_date = datetime.now(get_zone_info(timezone)).date()
    weekly_budget = await event_bus.send(
        GetWeeklyBudgetQuery(
            user_id=user_id,
            target_date=start_date,
            header_timezone=timezone,
        )
    )
    daily_calories = int(round(weekly_budget.get("adjusted_daily_calories") or 0))
    if daily_calories <= 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Meal recommendation target is unavailable",
        )
    try:
        plan = await event_bus.send(
            CreateThreeDayMealRecommendationCommand(
                user_id=user_id,
                idempotency_key=normalized_idempotency_key,
                start_date=start_date,
                timezone=timezone,
                daily_calories=daily_calories,
            )
        )
    except MealRecommendationCreationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.public_detail,
        ) from exc
    return _to_response(plan)


@router.post("/{plan_id}/slots/{slot_id}/swap", response_model=MealRecommendationPlanResponse)
async def swap_meal_recommendation_slot(
    plan_id: str,
    slot_id: str,
    body: SwapMealRecommendationSlotRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus=Depends(get_configured_event_bus),
) -> MealRecommendationPlanResponse:
    try:
        plan = await event_bus.send(
            SwapMealRecommendationSlotCommand(
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot_id,
                request_id=body.request_id,
                expected_version=body.expected_version,
                alternative_recipe_version_id=body.alternative_recipe_version_id,
                reason=body.reason,
            )
        )
    except MealRecommendationCreationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.public_detail) from exc
    return _to_response(plan)


@router.post("/{plan_id}/slots/{slot_id}/log", response_model=MealRecommendationPlanResponse)
async def log_recommended_meal(
    plan_id: str,
    slot_id: str,
    body: LogRecommendedMealRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus=Depends(get_configured_event_bus),
) -> MealRecommendationPlanResponse:
    try:
        plan = await event_bus.send(
            LogRecommendedMealCommand(
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot_id,
                request_id=body.request_id,
            )
        )
    except MealRecommendationCreationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.public_detail) from exc
    return _to_response(plan)


@router.get("/{plan_id}", response_model=MealRecommendationPlanResponse)
async def get_meal_recommendation_plan(
    plan_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus=Depends(get_configured_event_bus),
) -> MealRecommendationPlanResponse:
    """Read an owner-scoped durable recommendation plan."""

    plan = await event_bus.send(
        GetMealRecommendationPlanQuery(user_id=user_id, plan_id=plan_id)
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _to_response(plan)


def _to_response(
    plan: PersistedMealRecommendationPlan,
) -> MealRecommendationPlanResponse:
    return MealRecommendationPlanResponse(
        id=plan.id,
        status=plan.status,
        timezone=plan.timezone,
        start_date=plan.start_date,
        daily_calories=plan.daily_calories,
        algorithm_version=plan.algorithm_version,
        catalog_release_id=plan.catalog_release_id,
        allergy_evaluated=plan.allergy_evaluated,
        slots=[
            MealRecommendationSlotResponse(
                id=slot.id,
                slot_date=slot.slot_date,
                day_index=slot.day_index,
                meal_type=slot.meal_type,
                recipe_version_id=slot.recipe_version_id,
                target_calories=slot.target_calories,
                score=slot.score,
                position=slot.position,
                version=slot.version,
                logged_meal_id=slot.logged_meal_id,
                alternatives=[
                    MealRecommendationAlternativeResponse(
                        id=alternative.id,
                        recipe_version_id=alternative.recipe_version_id,
                        target_calories=alternative.target_calories,
                        score=alternative.score,
                        position=alternative.position,
                    )
                    for alternative in slot.alternatives
                ],
            )
            for slot in plan.slots
        ],
    )
