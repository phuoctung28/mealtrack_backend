import logging

from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from api.schemas.macros_schemas import (
    OnboardingChoicesRequest, MacrosCalculationResponse,
    ConsumedMacrosRequest, UpdatedMacrosResponse, DailyMacrosResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/macros",
    tags=["macros"],
)

@router.post("/calculate", status_code=status.HTTP_201_CREATED, response_model=MacrosCalculationResponse)
async def calculate_macros_from_onboarding(
    onboarding_data: OnboardingChoicesRequest,
    background_tasks: BackgroundTasks = None,
    # handler: MacrosCalculationHandler = Depends(get_macros_calculation_handler),
):
    """
    Send user onboard choices to ChatGPT and retrieve macros for each day.
    
    Should we return an approximate time to get? e.g. 6 months
    
    - Must priority endpoint
    - Uses AI to generate personalized macro targets based on user profile
    - Creates daily macro tracking entry
    """
    try:
        # TODO: Implement macro calculation using ChatGPT/AI service
        logger.info(f"Calculating macros for user: {onboarding_data.goal}, {onboarding_data.activity_level}")
        
        # Placeholder calculation - implement actual AI-based calculation
        # This should use ChatGPT or similar AI service to generate personalized recommendations
        
        # Basic BMR calculation (Mifflin-St Jeor Equation)
        if onboarding_data.gender == "male":
            bmr = 88.362 + (13.397 * onboarding_data.weight) + (4.799 * onboarding_data.height) - (5.677 * onboarding_data.age)
        else:
            bmr = 447.593 + (9.247 * onboarding_data.weight) + (3.098 * onboarding_data.height) - (4.330 * onboarding_data.age)
        
        # Activity multipliers
        activity_multipliers = {
            "sedentary": 1.2,
            "lightly_active": 1.375,
            "moderately_active": 1.55,
            "very_active": 1.725,
            "extra_active": 1.9
        }
        
        tdee = bmr * activity_multipliers.get(onboarding_data.activity_level, 1.375)
        
        # Goal adjustments
        if onboarding_data.goal == "lose_weight":
            target_calories = tdee - 500  # 1 lb per week
            daily_deficit = -500
        elif onboarding_data.goal == "gain_weight" or onboarding_data.goal == "build_muscle":
            target_calories = tdee + 300  # Moderate surplus
            daily_deficit = 300
        else:  # maintain_weight
            target_calories = tdee
            daily_deficit = 0
        
        # Macro distribution (common guidelines)
        protein_calories = target_calories * 0.25  # 25% protein
        carbs_calories = target_calories * 0.45    # 45% carbs
        fat_calories = target_calories * 0.30      # 30% fat
        
        target_macros = {
            "protein": round(protein_calories / 4, 1),  # 4 cal per gram
            "carbs": round(carbs_calories / 4, 1),      # 4 cal per gram
            "fat": round(fat_calories / 9, 1),          # 9 cal per gram
            "fiber": round(onboarding_data.weight * 0.35, 1)  # ~0.35g per kg body weight
        }
        
        recommendations = [
            f"Based on your {onboarding_data.goal} goal and {onboarding_data.activity_level} activity level",
            f"Aim for {int(target_calories)} calories per day",
            f"Focus on getting {target_macros['protein']}g protein to support your goals",
            "Drink plenty of water throughout the day",
            "Consider meal timing around your workouts"
        ]
        
        if onboarding_data.dietary_preferences:
            recommendations.append(f"We've considered your dietary preferences: {', '.join(onboarding_data.dietary_preferences)}")
        
        return MacrosCalculationResponse(
            target_calories=round(target_calories),
            target_macros=target_macros,
            estimated_timeline_months=onboarding_data.timeline_months or 6,
            bmr=round(bmr, 1),
            tdee=round(tdee, 1),
            daily_calorie_deficit_surplus=daily_deficit,
            recommendations=recommendations,
            user_macros_id="temp-user-macros-id"  # TODO: Generate actual ID
        )
        
    except Exception as e:
        logger.error(f"Error calculating macros: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating macros: {str(e)}"
        )

@router.post("/consumed", response_model=UpdatedMacrosResponse)
async def update_consumed_macros(
    consumed_data: ConsumedMacrosRequest,
    # handler: MacrosTrackingHandler = Depends(get_macros_tracking_handler)
):
    """
    Send consumed macros and retrieve updated macros left in a day.
    
    - Must priority endpoint
    - Updates daily macro consumption
    - Returns remaining macros and progress
    """
    try:
        # TODO: Implement macro consumption tracking
        logger.info(f"Updating consumed macros: {consumed_data.calories} calories")
        
        # Placeholder response - implement actual tracking
        # This should update the user's daily macro consumption
        
        # Example daily targets (should come from user's profile)
        target_calories = 2000.0
        target_macros = {
            "protein": 150.0,
            "carbs": 225.0,
            "fat": 67.0,
            "fiber": 25.0
        }
        
        # Example current consumption (should come from database)
        current_consumed_calories = 800.0 + consumed_data.calories
        current_consumed_macros = {
            "protein": 60.0 + consumed_data.macros.protein,
            "carbs": 90.0 + consumed_data.macros.carbs,
            "fat": 25.0 + consumed_data.macros.fat,
            "fiber": 12.0 + (consumed_data.macros.fiber or 0)
        }
        
        # Calculate remaining
        remaining_calories = max(0, target_calories - current_consumed_calories)
        remaining_macros = {
            "protein": max(0, target_macros["protein"] - current_consumed_macros["protein"]),
            "carbs": max(0, target_macros["carbs"] - current_consumed_macros["carbs"]),
            "fat": max(0, target_macros["fat"] - current_consumed_macros["fat"]),
            "fiber": max(0, target_macros["fiber"] - current_consumed_macros["fiber"])
        }
        
        # Calculate completion percentage
        completion_percentage = {
            "calories": min(100.0, (current_consumed_calories / target_calories) * 100),
            "protein": min(100.0, (current_consumed_macros["protein"] / target_macros["protein"]) * 100),
            "carbs": min(100.0, (current_consumed_macros["carbs"] / target_macros["carbs"]) * 100),
            "fat": min(100.0, (current_consumed_macros["fat"] / target_macros["fat"]) * 100)
        }
        
        # Check if goals are met
        is_goal_met = all(
            completion_percentage[key] >= 80.0  # 80% completion considered "met"
            for key in ["calories", "protein", "carbs", "fat"]
        )
        
        # Generate recommendations
        recommendations = []
        if completion_percentage["protein"] < 50:
            recommendations.append("Consider adding more protein-rich foods to reach your daily target")
        if completion_percentage["calories"] > 110:
            recommendations.append("You're close to exceeding your daily calorie target")
        if remaining_calories > 500:
            recommendations.append("You have room for a substantial meal or snack")
        if is_goal_met:
            recommendations.append("Great job! You're on track with your daily nutrition goals")
        
        return UpdatedMacrosResponse(
            user_macros_id="temp-user-macros-id",
            target_date="2024-01-01",
            target_calories=target_calories,
            target_macros=target_macros,
            consumed_calories=current_consumed_calories,
            consumed_macros=current_consumed_macros,
            remaining_calories=remaining_calories,
            remaining_macros=remaining_macros,
            completion_percentage=completion_percentage,
            is_goal_met=is_goal_met,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Error updating consumed macros: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating consumed macros: {str(e)}"
        )

@router.get("/daily", response_model=DailyMacrosResponse)
async def get_daily_macros(
    date: str = None,  # Optional date parameter, defaults to today
    # handler: MacrosTrackingHandler = Depends(get_macros_tracking_handler)
):
    """
    Get daily macro targets and current consumption for a specific date.
    
    - Returns current daily macro status
    - Defaults to today if no date provided
    """
    try:
        # TODO: Implement daily macro retrieval
        logger.info(f"Retrieving daily macros for date: {date or 'today'}")
        
        # Placeholder response - implement actual retrieval
        return DailyMacrosResponse(
            date=date or "2024-01-01",
            target_calories=2000.0,
            target_macros={
                "protein": 150.0,
                "carbs": 225.0,
                "fat": 67.0,
                "fiber": 25.0
            },
            consumed_calories=1200.0,
            consumed_macros={
                "protein": 90.0,
                "carbs": 135.0,
                "fat": 40.0,
                "fiber": 15.0
            },
            remaining_calories=800.0,
            remaining_macros={
                "protein": 60.0,
                "carbs": 90.0,
                "fat": 27.0,
                "fiber": 10.0
            },
            completion_percentage={
                "calories": 60.0,
                "protein": 60.0,
                "carbs": 60.0,
                "fat": 59.7
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving daily macros: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving daily macros: {str(e)}"
        ) 