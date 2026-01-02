"""
Meal suggestion API endpoints (Phase 06).
Includes both legacy endpoints and new session-based endpoints.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request.meal_suggestion_requests import (
    MealSuggestionRequest,
    SaveMealSuggestionRequest,
    RegenerateSuggestionsRequest,
    AcceptSuggestionRequest,
    RejectSuggestionRequest,
)
from src.api.schemas.response.meal_suggestion_responses import (
    MealSuggestionsResponse,
    SaveMealSuggestionResponse,
    SuggestionsListResponse,
    AcceptedMealResponse,
)
from src.api.mappers.meal_suggestion_mapper import (
    to_suggestions_list_response,
    to_accepted_meal_response,
)
from src.app.commands.meal_suggestion import (
    GenerateMealSuggestionsCommand,
    SaveMealSuggestionCommand,
    RegenerateSuggestionsCommand,
    AcceptSuggestionCommand,
    RejectSuggestionCommand,
    DiscardSessionCommand,
)
from src.app.queries.meal_suggestion import GetSessionSuggestionsQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-suggestions", tags=["Meal Suggestions"])

@router.post("/save", response_model=SaveMealSuggestionResponse)
async def save_meal_suggestion(
    request: SaveMealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
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
        
        # Create command
        command = SaveMealSuggestionCommand(
            user_id=user_id,
            suggestion_id=request.suggestion_id,
            name=request.name,
            description=request.description,
            meal_type=request.meal_type,
            estimated_cook_time_minutes=request.estimated_cook_time_minutes,
            calories=request.calories,
            protein=request.protein,
            carbs=request.carbs,
            fat=request.fat,
            ingredients_list=request.ingredients_list,
            instructions=request.instructions,
            meal_date=meal_date
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
async def generate_suggestions_v2(
    request: MealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [Phase 06] Generate 3 meal suggestions with session tracking.

    Uses meal_size (S/M/L/XL/OMAD) to calculate target calories from user's TDEE.
    Creates a session that tracks shown suggestions for regeneration.
    Session expires after 4 hours.
    """
    try:
        command = GenerateMealSuggestionsCommand(
            user_id=user_id,
            meal_type=request.meal_type,
            meal_size=request.meal_size.value,
            ingredients=request.ingredients,
            ingredient_image_url=request.ingredient_image_url,
            cooking_time_minutes=request.cooking_time_minutes.value,
        )

        session, suggestions = await event_bus.send(command)
        return to_suggestions_list_response(session, suggestions)

    except Exception as e:
        raise handle_exception(e) from e


@router.post("/regenerate", response_model=SuggestionsListResponse)
async def regenerate_suggestions(
    request: RegenerateSuggestionsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [Phase 06] Regenerate 3 NEW suggestions excluding previously shown.

    Requires session_id from initial generation.
    Excludes all previously shown suggestions plus explicitly passed exclude_ids.
    """
    try:
        command = RegenerateSuggestionsCommand(
            user_id=user_id,
            session_id=request.session_id,
            exclude_ids=request.exclude_ids,
        )

        session, suggestions = await event_bus.send(command)
        return to_suggestions_list_response(session, suggestions)

    except Exception as e:
        raise handle_exception(e) from e


@router.get("/{session_id}", response_model=SuggestionsListResponse)
async def get_session_suggestions(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [Phase 06] Get current session's suggestions.

    Retrieves all suggestions generated in this session.
    Returns 404 if session expired (4h TTL).
    """
    try:
        query = GetSessionSuggestionsQuery(
            user_id=user_id,
            session_id=session_id,
        )

        session, suggestions = await event_bus.send(query)
        return to_suggestions_list_response(session, suggestions)

    except Exception as e:
        raise handle_exception(e) from e


@router.post("/{suggestion_id}/accept", response_model=AcceptedMealResponse)
async def accept_suggestion(
    suggestion_id: str,
    request: AcceptSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [Phase 06] Accept suggestion with portion multiplier (1x-4x).

    Applies portion multiplier to macros and saves to meal history.
    Marks suggestion as accepted.
    """
    try:
        command = AcceptSuggestionCommand(
            user_id=user_id,
            suggestion_id=suggestion_id,
            portion_multiplier=request.portion_multiplier,
            consumed_at=request.consumed_at,
        )

        result = await event_bus.send(command)
        return to_accepted_meal_response(result)

    except Exception as e:
        raise handle_exception(e) from e


@router.post("/{suggestion_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_suggestion(
    suggestion_id: str,
    request: RejectSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [Phase 06] Reject suggestion with optional feedback.

    Marks suggestion as rejected. Feedback used for analytics/improvement.
    """
    try:
        command = RejectSuggestionCommand(
            user_id=user_id,
            suggestion_id=suggestion_id,
            feedback=request.feedback if hasattr(request, 'feedback') else None,
        )

        await event_bus.send(command)

    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [Phase 06] Discard entire suggestion session.

    Deletes session and all associated suggestions from cache.
    Used when user cancels the flow.
    """
    try:
        command = DiscardSessionCommand(
            user_id=user_id,
            session_id=session_id,
        )

        await event_bus.send(command)

    except Exception as e:
        raise handle_exception(e) from e
