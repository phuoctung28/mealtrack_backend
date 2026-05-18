"""Hydration-related request DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.model.hydration.hydration_entry import DrinkType


class LogHydrationRequest(BaseModel):
    """Request body for POST /v1/hydration/log."""

    drink_type: DrinkType = Field(..., description="Type of zero-calorie drink")
    volume_ml: int = Field(
        ..., gt=0, le=2000, description="Volume in millilitres (1–2000)"
    )
    logged_at: datetime = Field(
        ..., description="When the drink was consumed (ISO 8601, tz-aware)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "drink_type": "WATER",
                "volume_ml": 500,
                "logged_at": "2026-05-18T08:00:00+07:00",
            }
        }
    }


class UpdateHydrationGoalRequest(BaseModel):
    """Request body for PATCH /v1/users/me/hydration-goal.

    Bounds: 500–4000 ml (WHO lower bound → reasonable upper ceiling).
    The handler enforces the same bounds as a safety net.
    """

    goal_ml: int = Field(
        ...,
        ge=500,
        le=4000,
        description="Daily hydration target in millilitres (500–4000)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {"goal_ml": 2500}
        }
    }
