"""
Meal Discovery API endpoints (NM-67, NM-72).
POST /v1/meal-discovery/generate  — batch of 15 lightweight meals
GET  /v1/meal-discovery/image     — food image search (Pexels/Unsplash)
"""
import logging

from fastapi import APIRouter, Depends, Query, Request, Response

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.middleware.accept_language import get_request_language
from src.api.middleware.rate_limit import limiter
from src.api.schemas.request.meal_discovery_requests import MealDiscoveryRequest
from src.api.schemas.response.meal_discovery_responses import (
    DiscoveryBatchResponse,
    DiscoveryMealResponse,
    FoodImageResponse,
)
from src.app.commands.meal_discovery import GenerateDiscoveryCommand
from src.infra.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/meal-discovery", tags=["Meal Discovery"])


@router.post("/generate", response_model=DiscoveryBatchResponse)
@limiter.limit("10/minute")
async def generate_discovery_batch(
    request: Request,
    body: MealDiscoveryRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [NM-67] Generate a batch of 15 lightweight discovery meals.

    Returns diverse meal options for browsing. Pass session_id from a previous
    response as body.session_id to avoid repeated meals across batches.

    Rate limited to 10 requests/minute per user.
    Language is read from the Accept-Language header.
    """
    try:
        language = get_request_language(request)
        command = GenerateDiscoveryCommand(
            user_id=user_id,
            meal_type=body.meal_type,
            cuisine_filter=body.cuisine_filter,
            cooking_time=body.cooking_time,
            calorie_level=body.calorie_level,
            macro_focus=body.macro_focus,
            exclude_ids=body.exclude_ids,
            language=language,
        )
        session, meals = await event_bus.send(command)

        return DiscoveryBatchResponse(
            meals=[
                DiscoveryMealResponse(
                    id=m.id,
                    name=m.name,
                    name_en=m.name_en,
                    emoji=m.emoji,
                    cuisine=m.cuisine,
                    calories=m.calories,
                    protein=m.protein,
                    carbs=m.carbs,
                    fat=m.fat,
                    ingredients=m.ingredients,
                    image_search_query=m.image_search_query,
                    image_url=m.image_url,
                    image_source=m.image_source,
                )
                for m in meals
            ],
            batch_id=session.id,
            has_more=True,
        )
    except Exception as e:
        raise handle_exception(e)


@router.get("/image")
@limiter.limit("30/minute")
async def get_food_image(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="English food search query"),
):
    """
    [NM-72] Search for a food image by query string.

    Returns 200 with image data or 204 if no image found.
    Results are cached in-memory for 7 days.
    Rate limited to 30 requests/minute.
    """
    try:
        from src.domain.services.meal_discovery.food_image_search_service import (
            get_food_image_search_service,
        )
        image_service = get_food_image_search_service()
        result = await image_service.search_food_image(q)
        if result is None:
            return Response(status_code=204)
        return FoodImageResponse(
            url=result.url,
            thumbnail_url=result.thumbnail_url,
            source=result.source,
            photographer=result.photographer,
        )
    except Exception as e:
        logger.warning(f"Food image search failed for query '{q}': {e}")
        return Response(status_code=204)
