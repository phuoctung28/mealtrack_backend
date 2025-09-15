"""
Manual meal creation endpoint using USDA FDC items.
"""
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies.event_bus import get_configured_event_bus
from src.infra.event_bus import EventBus
from src.api.schemas.request.meal_requests import CreateManualMealFromFoodsRequest
from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand, ManualMealItem


router = APIRouter(prefix="/v1/meals", tags=["Meals"])


@router.post("/manual")
async def create_manual_meal(
    payload: CreateManualMealFromFoodsRequest,
    user_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        items = [ManualMealItem(fdc_id=i.fdc_id, quantity=i.quantity, unit=i.unit) for i in payload.items]
        cmd = CreateManualMealCommand(user_id=user_id, items=items, dish_name=payload.dish_name)
        meal = await event_bus.send(cmd)
        # Reuse mapper for response
        from src.api.mappers.meal_mapper import MealMapper
        return MealMapper.to_detailed_response(meal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
