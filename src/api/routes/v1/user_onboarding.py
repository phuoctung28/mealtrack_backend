"""
User onboarding API endpoints - Event-driven architecture.
"""
from fastapi import APIRouter, Depends

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request import OnboardingCompleteRequest
from src.api.schemas.response import OnboardingResponse, TdeeCalculationResponse
from src.app.commands.user import (
    SaveUserOnboardingCommand
)
from src.app.queries.user import (
    GetUserProfileQuery
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/user-onboarding", tags=["User Onboarding"])


@router.post("/save", response_model=OnboardingResponse)
async def save_onboarding_data(
    request: OnboardingCompleteRequest,
    user_id: str = "test_user",  # TODO: Get from auth context
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Save user onboarding data.
    
    Creates/updates:
    - User profile with physical attributes
    - Dietary preferences, health conditions, allergies
    - Fitness goals and activity level
    - Calculates TDEE and macro targets
    """
    try:
        # Create command
        command = SaveUserOnboardingCommand(
            user_id=user_id,
            age=request.personal_info.age,
            gender=request.personal_info.gender,
            height_cm=request.personal_info.height_cm,
            weight_kg=request.personal_info.weight_kg,
            body_fat_percentage=request.personal_info.body_fat_percentage,
            activity_level=request.goals.activity_level,
            fitness_goal=request.goals.fitness_goal,
            target_weight_kg=request.goals.target_weight_kg,
            meals_per_day=request.goals.meals_per_day,
            snacks_per_day=request.goals.snacks_per_day,
            dietary_preferences=request.preferences.dietary_preferences,
            health_conditions=request.preferences.health_conditions,
            allergies=request.preferences.allergies
        )
        
        # Send command
        result = await event_bus.send(command)
        
        return OnboardingResponse(
            message="Onboarding data saved successfully",
            user_id=user_id,
            profile_id=result['profile']['id'],
            tdee_calculation={
                "bmr": result['tdee']['bmr'],
                "tdee": result['tdee']['tdee'],
                "target_calories": result['tdee']['target_calories'],
                "macros": result['tdee']['macros']
            }
        )
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/summary/{user_id}")
async def get_onboarding_summary(
    user_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Get user's onboarding data summary."""
    try:
        # Create query
        query = GetUserProfileQuery(user_id=user_id)
        
        # Send query
        result = await event_bus.send(query)
        
        return result
        
    except Exception as e:
        raise handle_exception(e)


@router.post("/{user_id}/recalculate-tdee", response_model=TdeeCalculationResponse) 
async def recalculate_tdee(
    user_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Recalculate TDEE based on current profile."""
    try:
        # Get user profile first
        query = GetUserProfileQuery(user_id=user_id)
        profile_result = await event_bus.send(query)
        
        # Use TDEE result from profile query
        tdee_data = profile_result['tdee']
        
        return TdeeCalculationResponse(
            bmr=tdee_data['bmr'],
            tdee=tdee_data['tdee'],
            target_calories=tdee_data['target_calories'],
            activity_multiplier=tdee_data.get('activity_multiplier', 1.2),
            formula_used=tdee_data.get('formula_used', 'Mifflin-St Jeor'),
            macros=tdee_data['macros']
        )
        
    except Exception as e:
        raise handle_exception(e)