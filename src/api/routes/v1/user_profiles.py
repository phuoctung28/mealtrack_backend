"""
User profiles API endpoints - Event-driven architecture.
Handles user profile management and TDEE calculations.
"""
from fastapi import APIRouter, Depends

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.tdee_mapper import TdeeMapper
from src.api.schemas.request import OnboardingCompleteRequest, GoalEnum
from src.api.schemas.response import TdeeCalculationResponse
from src.app.commands.user import SaveUserOnboardingCommand
from src.app.queries.tdee import GetUserTdeeQuery
from src.domain.model.tdee import TdeeResponse, Goal
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/user-profiles", tags=["User Profiles"])


@router.post("/", response_model=bool)
async def save_user_onboarding(
    request: OnboardingCompleteRequest,
    user_id: str = "test_user",
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Save user onboarding data and return TDEE calculation.
    
    Creates/updates:
    - User profile with physical attributes
    - Dietary preferences, health conditions, allergies
    - Fitness goals and activity level
    - Meal preferences
    - Returns TDEE calculation and macro targets
    """
    try:
        # Create command
        command = SaveUserOnboardingCommand(
            user_id=user_id,
            age=request.age,
            gender=request.gender,
            height_cm=request.height,
            weight_kg=request.weight,
            body_fat_percentage=request.body_fat_percentage,
            activity_level=request.activity_level,
            fitness_goal=request.goal,
            target_weight_kg=request.target_weight,
            meals_per_day=request.meals_per_day,
            snacks_per_day=request.snacks_per_day,
            dietary_preferences=request.dietary_preferences,
            health_conditions=request.health_conditions,
            allergies=request.allergies
        )

        await event_bus.send(command)
        return True

    except Exception as e:
        raise handle_exception(e)

@router.get("/{user_id}/tdee", response_model=TdeeCalculationResponse)
async def get_user_tdee(
    user_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get user's current TDEE calculation based on their profile.
    
    Retrieves the user's current profile and calculates:
    - BMR using Mifflin-St Jeor or Katch-McArdle formula
    - TDEE based on activity level
    - Macro targets based on fitness goal
    """
    try:
        # Create query
        query = GetUserTdeeQuery(user_id=user_id)
        
        # Send query
        result = await event_bus.send(query)

        # Map goal string to enum
        goal_map = {
            'maintenance': Goal.MAINTENANCE,
            'cutting': Goal.CUTTING,
            'bulking': Goal.BULKING
        }
        
        # Create domain response
        from src.domain.model.tdee import MacroTargets
        domain_response = TdeeResponse(
            bmr=result["bmr"],
            tdee=result["tdee"],
            goal=goal_map[result["profile_data"]["fitness_goal"]],
            macros=MacroTargets(
                calories=result["macros"]["calories"],
                protein=result["macros"]["protein"],
                carbs=result["macros"]["carbs"],
                fat=result["macros"]["fat"]
            )
        )
        
        # Use mapper to convert to response DTO
        mapper = TdeeMapper()
        response = mapper.to_response_dto(domain_response)
        
        # Add additional metadata
        response.activity_multiplier = result["activity_multiplier"]
        response.formula_used = result["formula_used"]
        
        return response
        
    except Exception as e:
        raise handle_exception(e)