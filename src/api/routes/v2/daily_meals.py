from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import logging

from src.api.schemas.response import (
    DailyMealSuggestionsResponse,
    SingleMealSuggestionResponse,
    MealTypeEnum
)
from src.api.mappers.daily_meal_mapper import DailyMealMapper
from src.app.handlers.daily_meal_suggestion_handler import DailyMealSuggestionHandler
from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.infra.database.config import get_db
from src.infra.repositories.user_repository import UserRepository
from src.app.services.user_onboarding_service import UserOnboardingService
from src.domain.model.macro_targets import SimpleMacroTargets

router = APIRouter(prefix="/v2/daily-meals", tags=["Daily Meal Suggestions V2"])
logger = logging.getLogger(__name__)

# Initialize services
suggestion_service = DailyMealSuggestionService()
suggestion_handler = DailyMealSuggestionHandler(suggestion_service)


@router.post("/suggestions/{user_profile_id}", response_model=DailyMealSuggestionsResponse)
async def get_daily_meal_suggestions_by_profile(
    user_profile_id: str,
    db: Session = Depends(get_db)
):
    """
    Get 3-5 meal suggestions for a day based on user profile ID.
    
    This endpoint automatically:
    1. Fetches user profile data (age, gender, height, weight)
    2. Gets user preferences (dietary, health conditions, allergies)
    3. Gets user goals (activity level, fitness goal)
    4. Fetches or calculates TDEE and macros
    5. Generates personalized meal suggestions
    """
    try:
        logger.info(f"Getting daily meal suggestions for profile: {user_profile_id}")
        
        # Initialize repositories
        user_repo = UserRepository(db)
        
        # Get user profile
        from src.infra.database.models.user.profile import UserProfile
        profile = db.query(UserProfile).filter(
            UserProfile.id == user_profile_id
        ).first()
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get user data
        user_id = profile.user_id
        preferences = user_repo.get_user_preferences(user_id)
        goal = user_repo.get_current_user_goal(user_id)
        latest_tdee = user_repo.get_latest_tdee_calculation(user_id)
        
        if not goal:
            raise HTTPException(status_code=404, detail="User goal not found")
        
        # Prepare user data in the format expected by the handler
        user_data = {
            'age': profile.age,
            'gender': profile.gender,
            'height': profile.height_cm,
            'weight': profile.weight_kg,
            'activity_level': goal.activity_level,
            'goal': goal.fitness_goal,
            'dietary_preferences': [],
            'health_conditions': [],
            'target_calories': None,
            'target_macros': None
        }
        
        # Add preferences if available
        if preferences:
            user_data['dietary_preferences'] = [dp.preference for dp in preferences.dietary_preferences]
            user_data['health_conditions'] = [hc.condition for hc in preferences.health_conditions]
            # Note: allergies could be added here too if needed
        
        # Add TDEE data if available
        if latest_tdee:
            user_data['target_calories'] = latest_tdee.target_calories
            user_data['target_macros'] = SimpleMacroTargets(
                protein=latest_tdee.protein_grams,
                carbs=latest_tdee.carbs_grams,
                fat=latest_tdee.fat_grams
            )
        else:
            # Calculate TDEE if not available
            onboarding_service = UserOnboardingService(db)
            tdee_result = onboarding_service._calculate_tdee_and_macros(profile, goal)
            
            user_data['target_calories'] = tdee_result['tdee']
            user_data['target_macros'] = tdee_result['macros']
            
            # Optionally save the calculation
            tdee_calc = user_repo.save_tdee_calculation(
                user_id=user_id,
                user_profile_id=profile.id,
                user_goal_id=goal.id,
                bmr=tdee_result['bmr'],
                tdee=tdee_result['tdee'],
                target_calories=tdee_result['tdee'],
                macros=tdee_result['macros']
            )
        
        # Get meal suggestions
        result = suggestion_handler.get_daily_suggestions(user_data)
        
        # Map to response DTO
        target_calories = user_data['target_calories'] or 2000
        target_macros = user_data['target_macros'] or SimpleMacroTargets(
            protein=50.0,
            carbs=250.0,
            fat=65.0
        )
        
        # Create handler response format for mapper
        handler_response = {
            "date": result.date,
            "meal_count": len(result.meals),
            "meals": [meal.to_dict() for meal in result.meals],
            "daily_totals": {
                "calories": result.daily_calories,
                "protein": result.daily_totals.protein,
                "carbs": result.daily_totals.carbs,
                "fat": result.daily_totals.fat
            }
        }
        
        return DailyMealMapper.map_handler_response_to_dto(
            handler_response,
            target_calories,
            target_macros
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating daily meal suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate meal suggestions")


@router.post("/suggestions/{user_profile_id}/{meal_type}", response_model=SingleMealSuggestionResponse)
async def get_single_meal_suggestion_by_profile(
    user_profile_id: str,
    meal_type: MealTypeEnum,
    db: Session = Depends(get_db)
):
    """
    Get a single meal suggestion for a specific meal type based on user profile ID.
    
    Meal types: breakfast, lunch, dinner, snack
    """
    try:
        logger.info(f"Getting {meal_type} suggestion for profile: {user_profile_id}")
        
        # Initialize repositories
        user_repo = UserRepository(db)
        
        # Get user profile
        from src.infra.database.models.user.profile import UserProfile
        profile = db.query(UserProfile).filter(
            UserProfile.id == user_profile_id
        ).first()
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get user data
        user_id = profile.user_id
        preferences = user_repo.get_user_preferences(user_id)
        goal = user_repo.get_current_user_goal(user_id)
        latest_tdee = user_repo.get_latest_tdee_calculation(user_id)
        
        if not goal:
            raise HTTPException(status_code=404, detail="User goal not found")
        
        # Prepare user data
        user_data = {
            'age': profile.age,
            'gender': profile.gender,
            'height': profile.height_cm,
            'weight': profile.weight_kg,
            'activity_level': goal.activity_level,
            'goal': goal.fitness_goal,
            'dietary_preferences': [],
            'health_conditions': [],
            'target_calories': None,
            'target_macros': None
        }
        
        # Add preferences
        if preferences:
            user_data['dietary_preferences'] = [dp.preference for dp in preferences.dietary_preferences]
            user_data['health_conditions'] = [hc.condition for hc in preferences.health_conditions]
        
        # Add TDEE data
        if latest_tdee:
            user_data['target_calories'] = latest_tdee.target_calories
            user_data['target_macros'] = SimpleMacroTargets(
                protein=latest_tdee.protein_grams,
                carbs=latest_tdee.carbs_grams,
                fat=latest_tdee.fat_grams
            )
        else:
            # Calculate TDEE if not available
            onboarding_service = UserOnboardingService(db)
            tdee_result = onboarding_service._calculate_tdee_and_macros(profile, goal)
            
            user_data['target_calories'] = tdee_result['tdee']
            user_data['target_macros'] = tdee_result['macros']
        
        # Get specific meal suggestion
        meal = suggestion_handler.get_meal_by_type(user_data, meal_type.value)
        
        # Map to response DTO
        meal_response = DailyMealMapper.map_planned_meal_to_schema(meal)
        
        return SingleMealSuggestionResponse(meal=meal_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating meal suggestion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate meal suggestion")


@router.get("/profile/{user_profile_id}/summary")
async def get_meal_planning_data(
    user_profile_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all the data that would be used for meal planning for a given profile.
    
    This is useful for debugging and understanding what data is being used.
    """
    try:
        user_repo = UserRepository(db)
        
        # Get user profile
        from src.infra.database.models.user.profile import UserProfile
        profile = db.query(UserProfile).filter(
            UserProfile.id == user_profile_id
        ).first()
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get related data
        user_id = profile.user_id
        preferences = user_repo.get_user_preferences(user_id)
        goal = user_repo.get_current_user_goal(user_id)
        latest_tdee = user_repo.get_latest_tdee_calculation(user_id)
        
        # Build response
        response = {
            "profile": {
                "id": profile.id,
                "user_id": profile.user_id,
                "age": profile.age,
                "gender": profile.gender,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "body_fat_percentage": profile.body_fat_percentage,
                "is_current": profile.is_current
            },
            "goal": None,
            "preferences": {
                "dietary": [],
                "health_conditions": [],
                "allergies": []
            },
            "latest_tdee": None
        }
        
        if goal:
            response["goal"] = {
                "id": goal.id,
                "activity_level": goal.activity_level,
                "fitness_goal": goal.fitness_goal,
                "target_weight_kg": goal.target_weight_kg,
                "meals_per_day": goal.meals_per_day,
                "snacks_per_day": goal.snacks_per_day,
                "is_current": goal.is_current
            }
        
        if preferences:
            response["preferences"]["dietary"] = [dp.preference for dp in preferences.dietary_preferences]
            response["preferences"]["health_conditions"] = [hc.condition for hc in preferences.health_conditions]
            response["preferences"]["allergies"] = [a.allergen for a in preferences.allergies]
        
        if latest_tdee:
            response["latest_tdee"] = {
                "id": latest_tdee.id,
                "calculation_date": latest_tdee.calculation_date.isoformat(),
                "bmr": latest_tdee.bmr,
                "tdee": latest_tdee.tdee,
                "target_calories": latest_tdee.target_calories,
                "macros": {
                    "protein": latest_tdee.protein_grams,
                    "carbs": latest_tdee.carbs_grams,
                    "fat": latest_tdee.fat_grams
                }
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting meal planning data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))