from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Query
from api.schemas.macros_schemas import (
    OnboardingChoicesRequest, MacrosCalculationResponse,
    ConsumedMacrosRequest, UpdatedMacrosResponse, DailyMacrosResponse
)
import logging
from typing import Optional, Dict

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
    Track consumed macros from a specific meal.
    
    - Must priority endpoint
    - Updates daily macro consumption based on meal and portion consumed
    - Returns remaining macros and progress
    """
    try:
        # TODO: Implement meal-based macro consumption tracking
        logger.info(f"Updating consumed macros from meal {consumed_data.meal_id}")
        
        # Get meal information to calculate consumed nutrition
        # This would fetch the meal from the database/handler
        # For now, using placeholder meal nutrition data
        meal_nutrition = {
            "total_calories": 400.0,
            "total_weight_grams": 350.0,
            "calories_per_100g": 114.3,
            "macros_per_100g": {
                "protein": 8.5,
                "carbs": 15.2,
                "fat": 4.8,
                "fiber": 2.1
            },
            "total_macros": {
                "protein": 29.8,
                "carbs": 53.2,
                "fat": 16.8,
                "fiber": 7.4
            }
        }
        
        # Calculate actual consumed nutrition based on portion
        consumed_calories = meal_nutrition["total_calories"]
        consumed_macros = meal_nutrition["total_macros"]
        
        # If specific weight or portion percentage is provided, adjust
        if consumed_data.weight_grams:
            weight_ratio = consumed_data.weight_grams / meal_nutrition["total_weight_grams"]
            consumed_calories = meal_nutrition["total_calories"] * weight_ratio
            consumed_macros = {
                "protein": meal_nutrition["total_macros"]["protein"] * weight_ratio,
                "carbs": meal_nutrition["total_macros"]["carbs"] * weight_ratio,
                "fat": meal_nutrition["total_macros"]["fat"] * weight_ratio,
                "fiber": meal_nutrition["total_macros"]["fiber"] * weight_ratio
            }
        elif consumed_data.portion_percentage:
            portion_ratio = consumed_data.portion_percentage / 100.0
            consumed_calories = meal_nutrition["total_calories"] * portion_ratio
            consumed_macros = {
                "protein": meal_nutrition["total_macros"]["protein"] * portion_ratio,
                "carbs": meal_nutrition["total_macros"]["carbs"] * portion_ratio,
                "fat": meal_nutrition["total_macros"]["fat"] * portion_ratio,
                "fiber": meal_nutrition["total_macros"]["fiber"] * portion_ratio
            }
        
        logger.info(f"Calculated consumed nutrition: {consumed_calories} calories, {consumed_macros['protein']}g protein")
        
        # Example daily targets (should come from user's profile)
        target_calories = 2000.0
        target_macros = {
            "protein": 150.0,
            "carbs": 225.0,
            "fat": 67.0,
            "fiber": 25.0
        }
        
        # Example current consumption (should come from database)
        current_consumed_calories = 800.0 + consumed_calories
        current_consumed_macros = {
            "protein": 60.0 + consumed_macros["protein"],
            "carbs": 90.0 + consumed_macros["carbs"],
            "fat": 25.0 + consumed_macros["fat"],
            "fiber": 12.0 + consumed_macros["fiber"]
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
        
        # Generate meal-specific recommendations
        recommendations = []
        if consumed_data.weight_grams:
            recommendations.append(f"Tracked {consumed_data.weight_grams}g portion from meal {consumed_data.meal_id}")
        elif consumed_data.portion_percentage:
            recommendations.append(f"Tracked {consumed_data.portion_percentage}% of meal {consumed_data.meal_id}")
        else:
            recommendations.append(f"Tracked full meal {consumed_data.meal_id}")
            
        if completion_percentage["protein"] < 50:
            recommendations.append("Consider adding more protein-rich foods to reach your daily target")
        if completion_percentage["calories"] > 110:
            recommendations.append("You're close to exceeding your daily calorie target")
        if remaining_calories > 500:
            recommendations.append("You have room for another substantial meal")
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

@router.get("/meal/{meal_id}", response_model=Dict)
async def get_meal_macros(
    meal_id: str,
    weight_grams: Optional[float] = Query(None, gt=0, description="Calculate macros for specific weight in grams"),
    # meal_handler: MealHandler = Depends(get_meal_handler)
):
    """
    Get macros for a specific meal, optionally scaled to a specific weight.
    
    - Returns meal nutrition information for macro tracking
    - Supports weight-based scaling for portion control
    """
    try:
        logger.info(f"Retrieving macros for meal {meal_id}" + (f" at {weight_grams}g" if weight_grams else ""))
        
        # TODO: Implement actual meal retrieval
        # meal = meal_handler.get_meal(meal_id)
        # if not meal:
        #     raise HTTPException(status_code=404, detail=f"Meal with ID {meal_id} not found")
        
        # Placeholder meal data - replace with actual meal retrieval
        base_meal = {
            "meal_id": meal_id,
            "name": "Chicken Stir Fry",
            "total_calories": 420.0,
            "total_weight_grams": 350.0,
            "calories_per_100g": 120.0,
            "macros_per_100g": {
                "protein": 9.5,
                "carbs": 12.8,
                "fat": 5.2,
                "fiber": 2.8
            },
            "total_macros": {
                "protein": 33.3,
                "carbs": 44.8,
                "fat": 18.2,
                "fiber": 9.8
            }
        }
        
        # If specific weight is requested, calculate scaled values
        if weight_grams:
            weight_ratio = weight_grams / base_meal["total_weight_grams"]
            scaled_meal = {
                **base_meal,
                "actual_weight_grams": weight_grams,
                "actual_calories": round(base_meal["total_calories"] * weight_ratio, 1),
                "actual_macros": {
                    "protein": round(base_meal["total_macros"]["protein"] * weight_ratio, 1),
                    "carbs": round(base_meal["total_macros"]["carbs"] * weight_ratio, 1),
                    "fat": round(base_meal["total_macros"]["fat"] * weight_ratio, 1),
                    "fiber": round(base_meal["total_macros"]["fiber"] * weight_ratio, 1)
                }
            }
            return scaled_meal
        
        return base_meal
        
    except Exception as e:
        logger.error(f"Error retrieving meal macros: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving meal macros: {str(e)}"
        ) 