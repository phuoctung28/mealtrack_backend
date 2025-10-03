"""
Foods API routes: search and details via USDA.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies.event_bus import get_configured_event_bus
from src.infra.event_bus import EventBus
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery


router = APIRouter(prefix="/v1/foods", tags=["Foods"])


@router.get("/search")
async def search_foods(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        query = SearchFoodsQuery(query=q, limit=limit)
        return await event_bus.send(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fdc_id}/details")
async def get_food_details(
    fdc_id: int,
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        query = GetFoodDetailsQuery(fdc_id=fdc_id)
        return await event_bus.send(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
