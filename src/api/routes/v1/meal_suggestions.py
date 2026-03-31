"""
Meal suggestion API endpoints (Phase 06).
Simplified to only include generation endpoint.
"""

from fastapi import APIRouter, Depends, Request
from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.middleware.accept_language import get_request_language
from src.api.middleware.rate_limit import limiter
from src.api.mappers.meal_suggestion_mapper import to_suggestions_list_response
from src.api.schemas.request.meal_suggestion_requests import (
    MealSuggestionRequest,
    SaveMealSuggestionRequest,
)
from src.api.schemas.response.meal_suggestion_responses import (
    SuggestionsListResponse,
    SaveMealSuggestionResponse,
)
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
            time_available_minutes=body.cooking_time_minutes.value,
            session_id=body.session_id,
            language=language,
            servings=body.servings,
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


@router.post("/save", response_model=SaveMealSuggestionResponse)
async def save_meal_suggestion(
    http_request: Request,
    body: SaveMealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Save a meal suggestion as a regular meal in the meals table.

    This creates a Meal entity populated with the suggestion's nutrition data
    for the specified date so that it participates in daily macros and history.
    Language preference from Accept-Language header is persisted to meal_translation.
    """
    try:
        language = get_request_language(http_request)

        command = SaveMealSuggestionCommand(
            user_id=user_id,
            suggestion_id=body.suggestion_id,
            name=body.name,
            meal_type=body.meal_type,
            calories=body.calories or round(body.protein * 4 + body.carbs * 4 + body.fat * 9),
            protein=body.protein,
            carbs=body.carbs,
            fat=body.fat,
            description=body.description,
            estimated_cook_time_minutes=body.estimated_cook_time_minutes,
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
                for i in body.ingredients
            ],
            instructions=[
                i.model_dump() if hasattr(i, 'model_dump') else i
                for i in body.instructions
            ],
            portion_multiplier=body.portion_multiplier,
            meal_date=body.meal_date,
            cuisine_type=body.cuisine_type,
            origin_country=body.origin_country,
            emoji=body.emoji,
            language=language,
        )

        meal_id = await event_bus.send(command)

        return SaveMealSuggestionResponse(
            meal_id=meal_id,
            message="Meal suggestion saved successfully",
            meal_date=body.meal_date,
        )

    except Exception as e:
        raise handle_exception(e) from e
