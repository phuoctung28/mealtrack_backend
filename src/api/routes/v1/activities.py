import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Query

from src.api.dependencies import get_meal_handler
from src.api.schemas.response import ActivityResponse, ActivitiesListResponse
from src.app.handlers.meal_handler import MealHandler
from src.domain.model.meal import MealStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/activities",
    tags=["activities"],
)

@router.get("/daily", response_model=List[Dict])
async def get_daily_activities(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """
    Get all activities (meals and workouts) for a specific date.
    
    Returns a unified list of activities including:
    - Meal activities with nutrition data
    - Workout activities (placeholder for future implementation)
    
    Activities are sorted by timestamp in descending order (newest first).
    """
    try:
        # Parse date or use today
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            target_date = datetime.now()
        
        activities = []
        
        # Get meal activities for the date
        meal_activities = await _get_meal_activities(target_date, meal_handler)
        logger.info(f"Found {len(meal_activities)} meal activities for date {target_date.strftime('%Y-%m-%d')}")
        activities.extend(meal_activities)
        
        # Get workout activities for the date (placeholder)
        workout_activities = await _get_workout_activities(target_date)
        logger.info(f"Found {len(workout_activities)} workout activities for date {target_date.strftime('%Y-%m-%d')}")
        activities.extend(workout_activities)
        
        # Sort by timestamp (newest first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"Retrieved {len(activities)} total activities for date {target_date.strftime('%Y-%m-%d')}")
        return activities
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving daily activities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving activities: {str(e)}"
        )

async def _get_meal_activities(target_date: datetime, meal_handler: MealHandler) -> List[Dict]:
    """Get meal activities for a specific date from the existing meal system."""
    try:
        # Use the existing daily meal entries endpoint logic
        date_obj = target_date.date()
        
        # Get meals for the date from the meal handler
        meals = meal_handler.get_meals_by_date(date_obj)
        
        meal_activities = []
        for meal in meals:
            # Only include meals that have nutrition data
            # Include both READY and ENRICHING status as they both have nutrition data
            if not meal.nutrition or meal.status not in [MealStatus.READY, MealStatus.ENRICHING]:
                continue
                
            # Determine meal type based on time
            meal_time = meal.created_at
            meal_type = _determine_meal_type(meal_time)

            # Get meal name from nutrition data
            estimated_weight = 300.0  # Default weight in grams
            
            if meal.nutrition.food_items:
                # Try to get weight from first food item
                first_food = meal.nutrition.food_items[0]
                if first_food.unit and 'g' in first_food.unit.lower():
                    estimated_weight = first_food.quantity
                elif first_food.quantity > 10:  # Assume grams if quantity is large
                    estimated_weight = first_food.quantity
            
            # Check if meal has been updated with new weight
            if hasattr(meal, 'updated_weight_grams'):
                estimated_weight = meal.updated_weight_grams
            
            # Get image URL if available
            image_url = None
            if hasattr(meal, 'image') and meal.image:
                image_url = meal.image.url
            
            # Create meal activity format
            activity = {
                "id": meal.meal_id,
                "type": "meal",
                "timestamp": meal.created_at.isoformat() if meal.created_at else target_date.isoformat(),
                "title": meal.dish_name or "Unknown Meal",
                "meal_type": meal_type,
                "calories": meal.nutrition.calories if meal.nutrition else 0,
                "macros": {
                    "protein": meal.nutrition.macros.protein if meal.nutrition else 0,
                    "carbs": meal.nutrition.macros.carbs if meal.nutrition else 0,
                    "fat": meal.nutrition.macros.fat if meal.nutrition else 0,
                    "fiber": meal.nutrition.macros.fiber if meal.nutrition and hasattr(meal.nutrition.macros, 'fiber') else 0,
                },
                "quantity": estimated_weight,
                "status": meal.status.value if meal.status else "unknown",
                "image_url": image_url
            }
            meal_activities.append(activity)
        
        return meal_activities
        
    except Exception as e:
        logger.error(f"Error getting meal activities: {str(e)}", exc_info=True)
        return []

async def _get_workout_activities(target_date: datetime) -> List[Dict]:
    """Get workout activities for a specific date (placeholder implementation)."""
    try:
        # TODO: Implement actual workout activity retrieval
        # For now, return mock workout data for demonstration
        
        workout_activities = []
        
        # Add some mock workout data for today and yesterday for demo purposes
        today = datetime.now().date()
        target_day = target_date.date()
        
        if target_day == today:
            # Today's mock workouts
            workout_activities.extend([
                {
                    "id": "workout_morning_run",
                    "type": "workout",
                    "timestamp": target_date.replace(hour=10, minute=0).isoformat(),
                    "title": "Morning Run",
                    "description": "Park running trail",
                    "exercise_type": "running",
                    "duration_minutes": 35,
                    "calories_burned": 320,
                    "notes": "Good pace, felt energized"
                },
                {
                    "id": "workout_strength_training",
                    "type": "workout",
                    "timestamp": target_date.replace(hour=18, minute=30).isoformat(),
                    "title": "Strength Training",
                    "description": "Upper body workout at gym",
                    "exercise_type": "weightlifting",
                    "duration_minutes": 45,
                    "calories_burned": 280,
                    "notes": "Focus on chest and shoulders"
                }
            ])
        elif target_day == (today - timedelta(days=1)):
            # Yesterday's mock workout
            workout_activities.append({
                "id": "workout_yoga_session",
                "type": "workout",
                "timestamp": target_date.replace(hour=17, minute=0).isoformat(),
                "title": "Yoga Session",
                "description": "Evening relaxation yoga",
                "exercise_type": "yoga",
                "duration_minutes": 60,
                "calories_burned": 180,
                "notes": "Focused on flexibility and breathing"
            })
        
        return workout_activities
        
    except Exception as e:
        logger.error(f"Error getting workout activities: {str(e)}", exc_info=True)
        return []

def _determine_meal_type(meal_time):
    """Determine meal type based on time of day."""
    if not meal_time:
        return "snack"
    
    hour = meal_time.hour
    if 5 <= hour < 11:
        return "breakfast"
    elif 11 <= hour < 16:
        return "lunch"
    elif 16 <= hour < 22:
        return "dinner"
    else:
        return "snack"