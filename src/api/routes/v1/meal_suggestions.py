"""
Meal suggestion API endpoints (Phase 06).
Simplified to only include generation endpoint.
"""

from fastapi import APIRouter, Depends, Request

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.middleware.accept_language import get_request_language
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
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-suggestions", tags=["Meal Suggestions"])


@router.post("/generate", response_model=SuggestionsListResponse)
async def generate_suggestions(
    http_request: Request,
    request: MealSuggestionRequest,
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
        language = get_request_language(http_request)

        portion_type = request.get_effective_portion_type()

        command = GenerateMealSuggestionsCommand(
            user_id=user_id,
            meal_type=request.meal_type,
            meal_portion_type=portion_type.value,
            ingredients=request.ingredients,
            time_available_minutes=request.cooking_time_minutes.value,
            session_id=request.session_id,  # Pass session_id for regeneration
            language=language,
            servings=request.servings,  # Pass servings for ingredient/calorie scaling
        )

        session, suggestions = await event_bus.send(command)
        return to_suggestions_list_response(session, suggestions)

    except Exception as e:
        raise handle_exception(e) from e


# REMOVED: /regenerate endpoint is no longer needed.
# Use POST /generate with session_id parameter to regenerate with automatic exclusion.


@router.post("/save", response_model=SaveMealSuggestionResponse)
async def save_meal_suggestion(
    request: SaveMealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Save a meal suggestion to planned_meals table (daily meal plan).

    This adds the meal to the user's suggested meals for the specified date.
    Creates MealPlan and MealPlanDay if they don't exist.

    The meal will appear in the user's daily meal plan and can be consumed later.
    """
    try:
        command = SaveMealSuggestionCommand(
            user_id=user_id,
            suggestion_id=request.suggestion_id,
            name=request.name,
            meal_type=request.meal_type,
            calories=request.calories,
            protein=request.protein,
            carbs=request.carbs,
            fat=request.fat,
            description=request.description,
            estimated_cook_time_minutes=request.estimated_cook_time_minutes,
            ingredients_list=request.ingredients_list,
            instructions=request.instructions,
            portion_multiplier=request.portion_multiplier,
            meal_date=request.meal_date,
        )

        planned_meal_id = await event_bus.send(command)

        return SaveMealSuggestionResponse(
            planned_meal_id=planned_meal_id,
            message="Meal suggestion saved successfully",
            meal_date=request.meal_date,
        )

    except Exception as e:
        raise handle_exception(e) from e
