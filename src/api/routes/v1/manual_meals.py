"""
Manual meal creation endpoint using USDA FDC items.
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception, ValidationException
from src.api.schemas.request.meal_requests import CreateManualMealFromFoodsRequest
from src.api.schemas.response.meal_responses import ManualMealCreationResponse
from src.app.commands.meal.create_manual_meal_command import (
    CreateManualMealCommand,
    ManualMealItem,
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meals", tags=["Meals"])


@router.post("/manual", response_model=ManualMealCreationResponse)
async def create_manual_meal(
    payload: CreateManualMealFromFoodsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
) -> ManualMealCreationResponse:
    """
    Create a manual meal from USDA FDC items.

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:

        items = [
            ManualMealItem(fdc_id=i.fdc_id, quantity=i.quantity, unit=i.unit)
            for i in payload.items
        ]

        # Parse target_date if provided
        target_date = None
        if payload.target_date:
            try:
                target_date = datetime.strptime(payload.target_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationException(
                    message="Invalid date format. Use YYYY-MM-DD",
                    error_code="INVALID_DATE_FORMAT",
                    details={"date": payload.target_date}
                ) from e

        cmd = CreateManualMealCommand(
            user_id=user_id,
            items=items,
            dish_name=payload.dish_name,
            meal_type=payload.meal_type,
            target_date=target_date,
        )
        meal = await event_bus.send(cmd)

        return ManualMealCreationResponse(
            meal_id=meal.meal_id,
            status="success",
            message=f"Meal '{payload.dish_name}' created successfully",
            created_at=meal.created_at,
        )
    except Exception as e:
        raise handle_exception(e) from e
