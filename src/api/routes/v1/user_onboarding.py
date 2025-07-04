"""User onboarding endpoints with database persistence."""
import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.api.schemas.request import OnboardingCompleteRequest
from src.app.services.user_onboarding_service import UserOnboardingService
from src.infra.database.config import get_db

router = APIRouter(prefix="/v1/user-onboarding", tags=["User Onboarding"])
logger = logging.getLogger(__name__)


@router.post("/save")
async def save_onboarding_data(
    request: OnboardingCompleteRequest,
    user_id: str = "test_user",  # TODO: Get from auth header
    db: Session = Depends(get_db)
):
    """
    Save user onboarding data to the database.
    
    This endpoint:
    1. Creates/updates user profile with physical attributes
    2. Saves dietary preferences, health conditions, and allergies
    3. Records fitness goals and activity level
    4. Calculates and stores TDEE and macro targets
    
    Note: Currently uses a test user ID. In production, this should
    come from authentication headers.
    """
    try:
        logger.info(f"Saving onboarding data for user: {user_id}")
        
        # Initialize service
        service = UserOnboardingService(db)
        
        # Prepare data in expected format
        onboarding_data = {
            'personal_info': {
                'age': request.age,
                'gender': request.gender,
                'height': request.height,
                'weight': request.weight,
                'body_fat_percentage': getattr(request, 'body_fat_percentage', None)
            },
            'activity_level': {
                'activity_level': request.activity_level
            },
            'fitness_goals': {
                'fitness_goal': request.goal,
                'target_weight': getattr(request, 'target_weight', None)
            },
            'dietary_preferences': {
                'preferences': request.dietary_preferences or []
            },
            'health_conditions': {
                'conditions': request.health_conditions or []
            },
            'allergies': {
                'allergies': getattr(request, 'allergies', [])
            },
            'meal_preferences': {
                'meals_per_day': getattr(request, 'meals_per_day', 3),
                'snacks_per_day': getattr(request, 'snacks_per_day', 1)
            }
        }
        
        # Save to database
        result = service.save_onboarding_data(user_id, onboarding_data)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to save data'))
        
        return {
            "message": "Onboarding data saved successfully",
            "user_id": result['user_id'],
            "profile_id": result['profile_id'],
            "goal_id": result['goal_id'],
            "tdee_calculation": result['tdee_calculation']
        }
        
    except Exception as e:
        logger.error(f"Error saving onboarding data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{user_id}")
async def get_onboarding_summary(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a summary of user's onboarding data.
    
    Returns:
    - Personal info (age, gender, height, weight)
    - Fitness info (activity level, goals)
    - Preferences (dietary, health conditions, allergies)
    - Latest TDEE calculation
    """
    try:
        service = UserOnboardingService(db)
        summary = service.get_user_onboarding_summary(user_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="User data not found")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-tdee/{user_id}")
async def recalculate_tdee(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Recalculate TDEE based on current user profile and goals.
    
    Useful when user updates their weight or activity level.
    """
    try:
        from src.infra.repositories.user_repository import UserRepository
        
        repo = UserRepository(db)
        service = UserOnboardingService(db)
        
        # Get current data
        profile = repo.get_current_user_profile(user_id)
        goal = repo.get_current_user_goal(user_id)
        
        if not profile or not goal:
            raise HTTPException(status_code=404, detail="User profile or goal not found")
        
        # Calculate new TDEE
        tdee_result = service._calculate_tdee_and_macros(profile, goal)
        
        # Save calculation
        tdee_calc = repo.save_tdee_calculation(
            user_id=user_id,
            user_profile_id=profile.id,
            user_goal_id=goal.id,
            bmr=tdee_result['bmr'],
            tdee=tdee_result['tdee'],
            target_calories=tdee_result['target_calories'],
            macros=tdee_result['macros']
        )
        
        return {
            "message": "TDEE recalculated successfully",
            "calculation": {
                "id": tdee_calc.id,
                "date": tdee_calc.calculation_date.isoformat(),
                "bmr": tdee_calc.bmr,
                "tdee": tdee_calc.tdee,
                "target_calories": tdee_calc.target_calories,
                "macros": {
                    "protein": tdee_calc.protein_grams,
                    "carbs": tdee_calc.carbs_grams,
                    "fat": tdee_calc.fat_grams
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating TDEE: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


