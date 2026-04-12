"""
Meal suggestion API endpoints (Phase 06).
Simplified to only include generation endpoint.
"""

import logging

from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import Response

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.middleware.accept_language import get_request_language
from src.api.middleware.rate_limit import limiter
from src.api.mappers.meal_suggestion_mapper import (
    to_suggestions_list_response,
    to_discovery_batch_response,
)
from src.api.schemas.request.meal_suggestion_requests import (
    MealSuggestionRequest,
    SaveMealSuggestionRequest,
    DiscoverMealsRequest,
)
from src.api.schemas.response.meal_suggestion_responses import (
    SuggestionsListResponse,
    SaveMealSuggestionResponse,
    DiscoveryBatchResponse,
    FoodImageResponse,
)

logger = logging.getLogger(__name__)
from src.app.commands.meal_suggestion import (
    GenerateMealSuggestionsCommand,
    SaveMealSuggestionCommand,
    IngredientItem,
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-suggestions", tags=["Meal Suggestions"])


@router.post("/generate", response_model=SuggestionsListResponse)
@limiter.limit("5/minute")
async def generate_suggestions(
    request: Request,
    body: MealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [Phase 06] Generate 3 meal suggestions with session tracking.

    **Initial Generation (no session_id):**
    - Creates new session and generates 3 meal suggestions
    - Returns session_id for future regeneration

    **Regeneration (with session_id):**
    - Automatically excludes previously shown meals from the session
    - Generates 3 NEW different meal suggestions
    - No need for separate /regenerate endpoint!

    Uses meal_portion_type (snack/main/omad) to calculate target calories from user's TDEE.
    Session expires after 4 hours.

    Backward compatible: accepts deprecated meal_size (S/M/L/XL/OMAD) and maps to new types.

    Language preference is read from Accept-Language header.
    """
    try:
        # Get language from Accept-Language header via middleware
        language = get_request_language(request)

        portion_type = body.get_effective_portion_type()

        command = GenerateMealSuggestionsCommand(
            user_id=user_id,
            meal_type=body.meal_type,
            meal_portion_type=portion_type.value,
            ingredients=body.ingredients,
            time_available_minutes=(
                body.cooking_time_minutes.value if body.cooking_time_minutes else None
            ),
            session_id=body.session_id,
            language=language,
            # Strictly enforce 1 serving per suggestion regardless of client input.
            # Older clients may still send 2-4 but are coerced to 1 for consistency.
            servings=1,
            cooking_equipment=body.cooking_equipment,
            cuisine_region=body.cuisine_region,
            calorie_target=body.calorie_target,
            protein_target=body.protein_target,
            carbs_target=body.carbs_target,
            fat_target=body.fat_target,
        )

        session, suggestions = await event_bus.send(command)
        return to_suggestions_list_response(session, suggestions)

    except Exception as e:
        raise handle_exception(e) from e

@router.post("/discover", response_model=DiscoveryBatchResponse)
@limiter.limit("5/minute")
async def discover_meals(
    request: Request,
    body: DiscoverMealsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Generate 6 discovery meals (lightweight, no recipe steps in response).
    Supports pagination via session_id — previously shown meals are auto-excluded.
    """
    try:
        language = get_request_language(request)
        portion_type = body.get_effective_portion_type()

        command = GenerateMealSuggestionsCommand(
            user_id=user_id,
            meal_type=body.meal_type,
            meal_portion_type=portion_type.value,
            ingredients=body.ingredients,
            time_available_minutes=(
                body.cooking_time_minutes.value if body.cooking_time_minutes else None
            ),
            session_id=body.session_id,
            language=language,
            servings=1,
            cooking_equipment=[],
            cuisine_region=body.cuisine_region,
            calorie_target=body.calorie_target,
            protein_target=body.protein_target,
            carbs_target=body.carbs_target,
            fat_target=body.fat_target,
            suggestion_count=body.batch_size,
        )

        session, suggestions = await event_bus.send(command)

        # Fetch images in parallel for all meals (non-blocking, best-effort)
        from src.api.dependencies.food_image import get_food_image_service
        image_service = get_food_image_service()
        import asyncio
        image_tasks = [
            image_service.search_food_image(s.meal_name)
            for s in suggestions
        ]
        images = await asyncio.gather(*image_tasks, return_exceptions=True)

        # Attach images to response
        meal_images = {}
        for s, img in zip(suggestions, images):
            if img is not None and not isinstance(img, Exception):
                meal_images[s.id] = img

        return to_discovery_batch_response(session, suggestions, meal_images)

    except Exception as e:
        raise handle_exception(e) from e


@router.get("/image", response_model=FoodImageResponse)
@limiter.limit("30/minute")
async def get_food_image(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="English food search query"),
    _user_id: str = Depends(get_current_user_id),
):
    """Search for a food image by query. Returns 200 with image data or 204 if not found."""
    try:
        from src.api.dependencies.food_image import get_food_image_service
        image_service = get_food_image_service()
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


@router.post("/save", response_model=SaveMealSuggestionResponse)
async def save_meal_suggestion(
    request: SaveMealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Save a meal suggestion as a regular meal in the meals table.

    This creates a Meal entity populated with the suggestion's nutrition data
    for the specified date so that it participates in daily macros and history.
    """
    try:
        command = SaveMealSuggestionCommand(
            user_id=user_id,
            suggestion_id=request.suggestion_id,
            name=request.name,
            meal_type=request.meal_type,
            calories=request.calories or round(request.protein * 4 + request.carbs * 4 + request.fat * 9),
            protein=request.protein,
            carbs=request.carbs,
            fat=request.fat,
            description=request.description,
            estimated_cook_time_minutes=request.estimated_cook_time_minutes,
            ingredients=[
                IngredientItem(
                    name=i.name,
                    amount=i.amount,
                    unit=i.unit,
                    calories=i.calories,
                    protein=i.protein,
                    carbs=i.carbs,
                    fat=i.fat,
                )
                for i in request.ingredients
            ],
            instructions=[
                i.model_dump() if hasattr(i, 'model_dump') else i
                for i in request.instructions
            ],
            portion_multiplier=request.portion_multiplier,
            meal_date=request.meal_date,
            cuisine_type=request.cuisine_type,
            origin_country=request.origin_country,
            emoji=request.emoji,
        )

        meal_id = await event_bus.send(command)

        return SaveMealSuggestionResponse(
            meal_id=meal_id,
            message="Meal suggestion saved successfully",
            meal_date=request.meal_date,
        )

    except Exception as e:
        raise handle_exception(e) from e
