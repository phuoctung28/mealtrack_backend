"""
Meal suggestion API endpoints (Phase 06).
Simplified to only include generation endpoint.
"""

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.meal_suggestion_mapper import to_suggestions_list_response
from src.api.schemas.request.meal_suggestion_requests import MealSuggestionRequest
from src.api.schemas.response.meal_suggestion_responses import SuggestionsListResponse
from src.app.commands.meal_suggestion import GenerateMealSuggestionsCommand
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-suggestions", tags=["Meal Suggestions"])


# REMOVED: /save endpoint is no longer used.
# Meal suggestions are saved directly through the main meal creation flow.


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


