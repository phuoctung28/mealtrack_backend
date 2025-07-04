import logging

from fastapi import APIRouter, HTTPException

from src.api.schemas.request import (
    UserPreferencesRequest,
    MealTypeEnum
)
from src.api.schemas.response import (
    DailyMealSuggestionsResponse,
    SingleMealSuggestionResponse
)
from src.app.handlers.daily_meal_suggestion_handler import DailyMealSuggestionHandler
from src.domain.model.macro_targets import SimpleMacroTargets
from src.domain.model.tdee import (
    TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem
)
from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.domain.services.tdee_service import TdeeCalculationService

router = APIRouter(prefix="/v1/daily-meals", tags=["Daily Meal Suggestions"])
logger = logging.getLogger(__name__)

# Initialize services
suggestion_service = DailyMealSuggestionService()
suggestion_handler = DailyMealSuggestionHandler(suggestion_service)
tdee_service = TdeeCalculationService()


@router.post("/suggestions", response_model=DailyMealSuggestionsResponse)
async def get_daily_meal_suggestions(request: UserPreferencesRequest):
    """
    Get 3-5 meal suggestions for a day based on user onboarding preferences.
    
    This endpoint generates personalized meal suggestions considering:
    - User's physical attributes (age, gender, height, weight)
    - Activity level and fitness goals
    - Dietary preferences and restrictions
    - Health conditions
    - Calculated or provided calorie/macro targets
    """
    try:
        # Calculate TDEE and macros if not provided
        if not request.target_calories or not request.target_macros:
            # Convert to TDEE request format
            sex = Sex.MALE if request.gender.lower() == "male" else Sex.FEMALE
            
            activity_map = {
                "sedentary": ActivityLevel.SEDENTARY,
                "lightly_active": ActivityLevel.LIGHT,
                "moderately_active": ActivityLevel.MODERATE,
                "very_active": ActivityLevel.ACTIVE,
                "extra_active": ActivityLevel.EXTRA
            }
            
            goal_map = {
                "lose_weight": Goal.CUTTING,
                "maintain_weight": Goal.MAINTENANCE,
                "gain_weight": Goal.BULKING,
                "build_muscle": Goal.BULKING
            }
            
            tdee_request = TdeeRequest(
                age=request.age,
                sex=sex,
                height_cm=request.height,
                weight_kg=request.weight,
                activity_level=activity_map.get(request.activity_level, ActivityLevel.MODERATE),
                goal=goal_map.get(request.goal, Goal.MAINTENANCE),
                unit_system=UnitSystem.METRIC
            )
            
            tdee_result = tdee_service.calculate_tdee(tdee_request)
            
            # Add calculated values to user data
            user_data = request.dict(exclude={'target_macros'})
            user_data['target_calories'] = tdee_result.tdee
            user_data['target_macros'] = SimpleMacroTargets(
                protein=tdee_result.macros.protein,
                carbs=tdee_result.macros.carbs,
                fat=tdee_result.macros.fat
            )
        else:
            user_data = request.dict(exclude={'target_macros'})
            if request.target_macros:
                user_data['target_macros'] = request.target_macros
        
        # Get meal suggestions
        result = suggestion_handler.get_daily_suggestions(user_data)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return DailyMealSuggestionsResponse(
            date=result["date"],
            meal_count=result["meal_count"],
            meals=result["meals"],
            daily_totals=result["daily_totals"],
            target_totals=result["target_totals"]
        )
        
    except ValueError as e:
        logger.warning(f"Validation error in daily meal suggestions: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating daily meal suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate meal suggestions")


@router.post("/suggestions/{meal_type}", response_model=SingleMealSuggestionResponse)
async def get_single_meal_suggestion(
    meal_type: MealTypeEnum,
    request: UserPreferencesRequest
):
    """
    Get a single meal suggestion for a specific meal type.
    
    Meal types: breakfast, lunch, dinner, snack
    """
    try:
        # Calculate TDEE and macros if not provided
        if not request.target_calories or not request.target_macros:
            # Similar calculation as above
            sex = Sex.MALE if request.gender.lower() == "male" else Sex.FEMALE
            
            activity_map = {
                "sedentary": ActivityLevel.SEDENTARY,
                "lightly_active": ActivityLevel.LIGHT,
                "moderately_active": ActivityLevel.MODERATE,
                "very_active": ActivityLevel.ACTIVE,
                "extra_active": ActivityLevel.EXTRA
            }
            
            goal_map = {
                "lose_weight": Goal.CUTTING,
                "maintain_weight": Goal.MAINTENANCE,
                "gain_weight": Goal.BULKING,
                "build_muscle": Goal.BULKING
            }
            
            tdee_request = TdeeRequest(
                age=request.age,
                sex=sex,
                height_cm=request.height,
                weight_kg=request.weight,
                activity_level=activity_map.get(request.activity_level, ActivityLevel.MODERATE),
                goal=goal_map.get(request.goal, Goal.MAINTENANCE),
                unit_system=UnitSystem.METRIC
            )
            
            tdee_result = tdee_service.calculate_tdee(tdee_request)
            
            user_data = request.dict(exclude={'target_macros'})
            user_data['target_calories'] = tdee_result.tdee
            user_data['target_macros'] = SimpleMacroTargets(
                protein=tdee_result.macros.protein,
                carbs=tdee_result.macros.carbs,
                fat=tdee_result.macros.fat
            )
        else:
            user_data = request.dict(exclude={'target_macros'})
            if request.target_macros:
                user_data['target_macros'] = request.target_macros
        
        # Get specific meal suggestion
        result = suggestion_handler.get_meal_by_type(user_data, meal_type.value)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return SingleMealSuggestionResponse(meal=result["meal"])
        
    except ValueError as e:
        logger.warning(f"Validation error in meal suggestion: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating meal suggestion: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate meal suggestion")


@router.get("/health")
async def daily_meals_health():
    """Check if daily meal suggestions service is healthy"""
    return {
        "status": "healthy",
        "service": "daily_meal_suggestions",
        "features": [
            "personalized_daily_suggestions",
            "single_meal_generation",
            "onboarding_integration",
            "macro_calculation"
        ]
    }