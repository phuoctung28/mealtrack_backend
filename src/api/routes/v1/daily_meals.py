"""
Daily meal suggestions API endpoints - Event-driven architecture.
"""
from typing import Optional

from fastapi import APIRouter, Depends

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.daily_meal_mapper import DailyMealMapper
from src.api.schemas.request import UserPreferencesRequest, MealTypeEnum
from src.api.schemas.response import (
    DailyMealSuggestionsResponse,
    SingleMealSuggestionResponse
)
from src.app.commands.daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand
)
from src.app.queries.daily_meal import (
    GetMealSuggestionsForProfileQuery,
    GetSingleMealForProfileQuery,
    GetMealPlanningSummaryQuery
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/daily-meals", tags=["Daily Meal Suggestions"])


@router.post("/suggestions", response_model=DailyMealSuggestionsResponse)
async def get_daily_meal_suggestions(
    request: Optional[UserPreferencesRequest] = None,
    user_profile_id: Optional[str] = None,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get 3-5 meal suggestions for a day in a single request.
    
    This endpoint generates all daily meals (breakfast, lunch, dinner, snack) 
    in one unified API call, ensuring better meal coordination and variety.
    
    Two modes supported:
    1. Profile-based (preferred): Provide user_profile_id
    2. Direct preferences: Provide full UserPreferencesRequest
    
    Profile-based suggestions use stored user data including:
    - User profile (age, gender, height, weight)
    - Preferences (dietary, health conditions, allergies)
    - Goals (activity level, fitness goal)
    - Calculated TDEE and macros
    """
    try:
        if user_profile_id:
            # Use profile-based query (preferred v2 approach)
            query = GetMealSuggestionsForProfileQuery(user_profile_id=user_profile_id)
            result = await event_bus.send(query)
        elif request:
            # Use direct command (legacy v1 approach)
            command = GenerateDailyMealSuggestionsCommand(
                age=request.age,
                gender=request.gender,
                height=request.height,
                weight=request.weight,
                activity_level=request.activity_level,
                goal=request.goal,
                dietary_preferences=request.dietary_preferences,
                health_conditions=request.health_conditions,
                target_calories=request.target_calories,
                target_macros=request.target_macros.dict() if request.target_macros else None
            )
            result = await event_bus.send(command)
        else:
            raise ValueError("Either user_profile_id or request data must be provided")
        
        # Use mapper to convert to response
        return DailyMealMapper.map_to_suggestions_response(result)
        
    except Exception as e:
        raise handle_exception(e)


@router.post("/suggestions/{meal_type}", response_model=SingleMealSuggestionResponse)
async def get_single_meal_suggestion(
    meal_type: MealTypeEnum,
    request: Optional[UserPreferencesRequest] = None,
    user_profile_id: Optional[str] = None,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get a single meal suggestion for a specific meal type.
    
    Meal types: breakfast, lunch, dinner, snack
    
    Two modes supported:
    1. Profile-based (preferred): Provide user_profile_id
    2. Direct preferences: Provide full UserPreferencesRequest
    """
    try:
        if user_profile_id:
            # Use profile-based query (preferred v2 approach)
            query = GetSingleMealForProfileQuery(
                user_profile_id=user_profile_id,
                meal_type=meal_type.value
            )
            result = await event_bus.send(query)
            # Direct response for profile-based query
            return SingleMealSuggestionResponse(meal=result["meal"])
        elif request:
            # Use direct command (legacy v1 approach)
            command = GenerateSingleMealCommand(
                meal_type=meal_type.value,
                age=request.age,
                gender=request.gender,
                height=request.height,
                weight=request.weight,
                activity_level=request.activity_level,
                goal=request.goal,
                dietary_preferences=request.dietary_preferences,
                health_conditions=request.health_conditions,
                target_calories=request.target_calories,
                target_macros=request.target_macros.dict() if request.target_macros else None
            )
            result = await event_bus.send(command)
            # Use mapper for command-based response
            mapped_result = DailyMealMapper.map_to_single_meal_response(result)
            return SingleMealSuggestionResponse(**mapped_result)
        else:
            raise ValueError("Either user_profile_id or request data must be provided")
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/profile/{user_profile_id}/summary")
async def get_meal_planning_summary(
    user_profile_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get meal planning data summary for a user profile.
    
    Returns user profile data, preferences, and calculated targets.
    Useful for debugging and verifying meal planning inputs.
    """
    try:
        # Create query
        query = GetMealPlanningSummaryQuery(user_profile_id=user_profile_id)
        
        # Send query
        result = await event_bus.send(query)
        
        return result
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/health")
async def daily_meals_health():
    """Check if daily meal suggestions service is healthy."""
    return {
        "status": "healthy",
        "service": "daily_meal_suggestions",
        "features": [
            "personalized_daily_suggestions",
            "single_meal_generation",
            "profile_based_suggestions",
            "direct_preferences_support",
            "onboarding_integration",
            "macro_calculation"
        ]
    }