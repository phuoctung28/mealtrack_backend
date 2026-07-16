"""Support models and helpers for meal recommendation routes."""

from __future__ import annotations

from time import perf_counter
from typing import Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator

from src.api.schemas.response.meal_recommendation_responses import (
    MealRecommendationAlternativeResponse,
    MealRecommendationPlanResponse,
    MealRecommendationSlotResponse,
)
from src.app.services.meal_recommendation_analytics_service import (
    MealRecommendationAnalyticsService,
)
from src.app.services.meal_recommendation_cohort_service import (
    MealRecommendationCohortService,
)
from src.domain.model.meal_recommendation import PersistedMealRecommendationPlan
from src.observability import distribution_metric, increment_metric, log_event


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


def ensure_recommendations_enabled(
    user_id: str,
    cohort_service: MealRecommendationCohortService,
    *,
    operation: str,
) -> None:
    if cohort_service.is_enabled_for_user(user_id):
        return
    increment_metric(
        "meal_recommendation.requests",
        attributes={
            "component": "meal_recommendation",
            "operation": operation,
            "status": "disabled",
        },
    )
    log_event(
        "info",
        "meal_recommendation.disabled",
        attributes={
            "component": "meal_recommendation",
            "operation": operation,
            "status": "disabled",
        },
    )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Meal recommendations are not available",
    )


def record_operation_latency(operation: str, started: float, status_value: str) -> None:
    elapsed_ms = (perf_counter() - started) * 1000
    attributes = {
        "component": "meal_recommendation",
        "operation": operation,
        "status": status_value,
    }
    distribution_metric(
        "meal_recommendation.operation.latency_ms",
        elapsed_ms,
        unit="millisecond",
        attributes=attributes,
    )
    increment_metric("meal_recommendation.requests", attributes=attributes)


async def capture_plan_events(
    analytics_service: MealRecommendationAnalyticsService,
    *,
    user_id: str,
    plan: PersistedMealRecommendationPlan,
    events: tuple[str, ...],
) -> None:
    for event in events:
        await analytics_service.capture_plan_response(
            user_id=user_id,
            event=event,
            plan=plan,
        )


def to_response(
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
