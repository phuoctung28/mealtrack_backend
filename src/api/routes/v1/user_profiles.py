"""
User profiles API endpoints - Event-driven architecture.
Handles user profile management and TDEE calculations.
"""
from datetime import date

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.tdee_mapper import TdeeMapper
from src.api.schemas.request import OnboardingCompleteRequest
from src.api.schemas.request.user_profile_update_requests import UpdateMetricsRequest
from src.api.schemas.response import TdeeCalculationResponse, UserMetricsResponse
from src.app.commands.user import SaveUserOnboardingCommand
from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
from src.app.queries.tdee import GetUserTdeeQuery
from src.app.queries.user import GetUserMetricsQuery
from src.domain.model.user import TdeeResponse, Goal, MacroTargets
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/user-profiles", tags=["User Profiles"])


@router.post("/", response_model=None)
async def save_user_onboarding(
    request: OnboardingCompleteRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Save user onboarding data and return TDEE calculation.

    Creates/updates:
    - User profile with physical attributes
    - Pain points and dietary preferences
    - Fitness goals, job_type and training frequency
    - Meal preferences
    - Returns TDEE calculation and macro targets

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        # Compute age from DOB (validate date is real — e.g., reject Feb 31)
        try:
            dob = date(request.birth_year, request.birth_month, request.birth_day)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Invalid birth date")
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Create command
        command = SaveUserOnboardingCommand(
            user_id=user_id,
            age=age,
            gender=request.gender,
            height_cm=request.height,
            weight_kg=request.weight,
            body_fat_percentage=request.body_fat_percentage,
            job_type=request.job_type,
            training_days_per_week=request.training_days_per_week,
            training_minutes_per_session=request.training_minutes_per_session,
            fitness_goal=request.goal,
            pain_points=request.pain_points,
            dietary_preferences=request.dietary_preferences,
            meals_per_day=request.meals_per_day,
            referral_sources=request.referral_sources,
            training_level=request.training_level,
            date_of_birth=dob,
            target_weight_kg=request.target_weight_kg,
        )

        await event_bus.send(command)
        return True

    except Exception as e:
        raise handle_exception(e) from e

@router.get("/metrics", response_model=UserMetricsResponse)
async def get_user_metrics(
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get user's current metrics for settings display.
    
    Retrieves the user's current profile metrics including:
    - Physical attributes (age, gender, height, weight, body fat)
    - Activity level
    - Fitness goal
    - Target weight
    
    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        # Create query
        query = GetUserMetricsQuery(user_id=user_id)
        
        # Send query
        result = await event_bus.send(query)
        
        return UserMetricsResponse(**result)
        
    except Exception as e:
        raise handle_exception(e) from e


@router.get("/tdee", response_model=TdeeCalculationResponse)
async def get_user_tdee(
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get user's current TDEE calculation based on their profile.
    
    Retrieves the user's current profile and calculates:
    - BMR using Mifflin-St Jeor or Katch-McArdle formula
    - TDEE based on job type and training frequency
    - Macro targets based on fitness goal
    
    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        # Create query
        query = GetUserTdeeQuery(user_id=user_id)
        
        # Send query
        result = await event_bus.send(query)

        # Map goal string to enum
        goal_map = {
            'cut': Goal.CUT,
            'bulk': Goal.BULK,
            'recomp': Goal.RECOMP
        }

        # Create domain response
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
        raise handle_exception(e) from e

@router.post("/metrics", response_model=TdeeCalculationResponse)
async def update_user_metrics(
    request: UpdateMetricsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Update user metrics (weight, job_type, training_days_per_week, training_minutes_per_session, body fat, fitness goal) and return updated TDEE/macros.

    Unified endpoint for profile updates.

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        # Update metrics (including optional fitness goal)
        command = UpdateUserMetricsCommand(
            user_id=user_id,
            weight_kg=request.weight_kg,
            job_type=request.job_type,
            training_days_per_week=request.training_days_per_week,
            training_minutes_per_session=request.training_minutes_per_session,
            body_fat_percent=request.body_fat_percent,
            fitness_goal=request.fitness_goal.value if request.fitness_goal else None,
            training_level=request.training_level.value if request.training_level else None,
        )

        await event_bus.send(command)

        # Return updated TDEE/macros
        query = GetUserTdeeQuery(user_id=user_id)
        result = await event_bus.send(query)

        goal_map = {
            'cut': Goal.CUT,
            'bulk': Goal.BULK,
            'recomp': Goal.RECOMP
        }

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

        mapper = TdeeMapper()
        response = mapper.to_response_dto(domain_response)
        response.activity_multiplier = result["activity_multiplier"]
        response.formula_used = result["formula_used"]
        return response

    except Exception as e:
        raise handle_exception(e) from e
