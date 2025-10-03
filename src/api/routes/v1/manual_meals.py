"""
Manual meal creation endpoint using USDA FDC items.
"""
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.schemas.request.meal_requests import CreateManualMealFromFoodsRequest
from src.api.schemas.response.meal_responses import ManualMealCreationResponse
from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand, ManualMealItem
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meals", tags=["Meals"])


@router.post("/manual", response_model=ManualMealCreationResponse)
async def create_manual_meal(
    payload: CreateManualMealFromFoodsRequest,
    user_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus),
) -> ManualMealCreationResponse:
    try:
        items = [ManualMealItem(fdc_id=i.fdc_id, quantity=i.quantity, unit=i.unit) for i in payload.items]
        cmd = CreateManualMealCommand(user_id=user_id, items=items, dish_name=payload.dish_name)
        meal = await event_bus.send(cmd)
        
        return ManualMealCreationResponse(
            meal_id=meal.meal_id,
            status="success",
            message=f"Manual meal '{payload.dish_name}' created successfully",
            created_at=meal.created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
