"""
Foods API routes: search and details via USDA.

Uses a lightweight singleton event bus to avoid re-initializing
heavy services (Cloudinary, Gemini, etc.) on every request.
"""
from fastapi import APIRouter, HTTPException, Query

from src.api.dependencies.event_bus import get_food_search_event_bus
from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery
from src.app.queries.food.search_foods_query import SearchFoodsQuery

router = APIRouter(prefix="/v1/foods", tags=["Foods"])


@router.get("/search")
async def search_foods(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    """Search foods using lightweight singleton event bus."""
    try:
        event_bus = get_food_search_event_bus()
        query = SearchFoodsQuery(query=q, limit=limit)
        return await event_bus.send(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fdc_id}/details")
async def get_food_details(
    fdc_id: int,
):
    """Get food details using lightweight singleton event bus."""
    try:
        event_bus = get_food_search_event_bus()
        query = GetFoodDetailsQuery(fdc_id=fdc_id)
        return await event_bus.send(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
