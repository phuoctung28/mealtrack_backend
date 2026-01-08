"""
Meal suggestion API endpoints (Phase 06).
Includes both legacy endpoints and new session-based endpoints.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.meal_suggestion_mapper import (
    to_suggestions_list_response,
)
from src.api.schemas.request.meal_suggestion_requests import (
    MealSuggestionRequest,
    SaveMealSuggestionRequest,
)
from src.api.schemas.response.meal_suggestion_responses import (
    SaveMealSuggestionResponse,
    SuggestionsListResponse,
)
from src.app.commands.meal_suggestion import (
    GenerateMealSuggestionsCommand,
    SaveMealSuggestionCommand,
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-suggestions", tags=["Meal Suggestions"])


@router.post("/save", response_model=SaveMealSuggestionResponse)
async def save_meal_suggestion(
    request: SaveMealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Save a selected meal suggestion to the user's meal history.

    This endpoint saves a meal suggestion to the user's planned meals for a specific date.
    The meal can then be viewed in the user's meal plan and tracked in their daily nutrition.

    Authentication required: User ID is automatically extracted from the Firebase token.

    Parameters:
    - suggestion_id: ID of the suggestion to save - REQUIRED
    - name: Name of the meal - REQUIRED
    - description: Description of the meal - OPTIONAL
    - meal_type: Type of meal (breakfast, lunch, dinner, snack) - REQUIRED
    - estimated_cook_time_minutes: Total cooking time - REQUIRED
    - calories: Calories for the meal - REQUIRED
    - protein: Protein in grams - REQUIRED
    - carbs: Carbohydrates in grams - REQUIRED
    - fat: Fat in grams - REQUIRED
    - ingredients_list: List of ingredients - OPTIONAL
    - instructions: Cooking instructions - OPTIONAL
    - meal_date: Date to save the meal for (YYYY-MM-DD), defaults to today - OPTIONAL

    Returns:
    - success: Whether the save was successful
    - message: Status message
    - meal_id: ID of the saved meal in the database
    - meal_date: Date the meal was saved for
    """
    try:
        # Parse meal date if provided
        meal_date = None
        if request.meal_date:
            try:
                meal_date = datetime.strptime(request.meal_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("meal_date must be in YYYY-MM-DD format")
        else:
            meal_date = date.today()

        # Apply portion multiplier to macros before saving
        multiplier = request.portion_multiplier or 1
        scaled_calories = int(request.calories * multiplier)
        scaled_protein = request.protein * multiplier
        scaled_carbs = request.carbs * multiplier
        scaled_fat = request.fat * multiplier

        # Create command with scaled macros
        command = SaveMealSuggestionCommand(
            user_id=user_id,
            suggestion_id=request.suggestion_id,
            name=request.name,
            description=request.description,
            meal_type=request.meal_type,
            estimated_cook_time_minutes=request.estimated_cook_time_minutes,
            calories=scaled_calories,
            protein=scaled_protein,
            carbs=scaled_carbs,
            fat=scaled_fat,
            ingredients_list=request.ingredients_list,
            instructions=request.instructions,
            meal_date=meal_date,
        )

        # Execute the command
        result = await event_bus.send(command)

        # Return response
        return SaveMealSuggestionResponse(**result)

    except Exception as e:
        raise handle_exception(e) from e


# ============================================================================
# Phase 06: New Session-Based Endpoints
# ============================================================================


@router.post("/generate", response_model=SuggestionsListResponse)
async def generate_suggestions(
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
    """
    try:
        portion_type = request.get_effective_portion_type()

        command = GenerateMealSuggestionsCommand(
            user_id=user_id,
            meal_type=request.meal_type,
            meal_portion_type=portion_type.value,
            ingredients=request.ingredients,
            time_available_minutes=request.cooking_time_minutes.value,
            session_id=request.session_id,  # Pass session_id for regeneration
        )

        session, suggestions = await event_bus.send(command)
        return to_suggestions_list_response(session, suggestions)

    except Exception as e:
        raise handle_exception(e) from e


# REMOVED: /regenerate endpoint is no longer needed.
# Use POST /generate with session_id parameter to regenerate with automatic exclusion.


