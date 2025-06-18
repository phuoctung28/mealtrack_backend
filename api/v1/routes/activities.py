import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Query

from api.dependencies import get_meal_handler
from api.schemas.activity_schemas import ActivityResponse, ActivitiesListResponse
from app.handlers.meal_handler import MealHandler

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
        activities.extend(meal_activities)
        
        # Get workout activities for the date (placeholder)
        workout_activities = await _get_workout_activities(target_date)
        activities.extend(workout_activities)
        
        # Sort by timestamp (newest first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"Retrieved {len(activities)} activities for date {target_date.strftime('%Y-%m-%d')}")
        return activities
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving daily activities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving activities: {str(e)}"
        )

@router.post("/workout", response_model=Dict)
async def add_workout_activity(
    workout_data: Dict
):
    """
    Add a new workout activity.
    
    This is a placeholder endpoint for future workout tracking functionality.
    Currently returns a mock response for development purposes.
    """
    try:
        # TODO: Implement actual workout activity storage
        logger.info("Adding workout activity (placeholder)")
        
        # Mock workout activity creation
        activity_id = f"workout_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "activity_id": activity_id,
            "status": "created",
            "message": "Workout activity tracking will be implemented in future versions"
        }
        
    except Exception as e:
        logger.error(f"Error adding workout activity: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding workout activity: {str(e)}"
        )

@router.delete("/workout/{activity_id}")
async def delete_workout_activity(activity_id: str):
    """
    Delete a workout activity.
    
    This is a placeholder endpoint for future workout tracking functionality.
    """
    try:
        # TODO: Implement actual workout activity deletion
        logger.info(f"Deleting workout activity {activity_id} (placeholder)")
        
        return {
            "status": "deleted",
            "message": "Workout activity deletion will be implemented in future versions"
        }
        
    except Exception as e:
        logger.error(f"Error deleting workout activity: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting workout activity: {str(e)}"
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
            # Determine meal type based on time
            meal_time = meal.created_at
            meal_type = _determine_meal_type(meal_time)
            
            # Create meal activity format
            activity = {
                "id": meal.meal_id,
                "type": "meal",
                "timestamp": meal.created_at.isoformat() if meal.created_at else target_date.isoformat(),
                "title": meal.meal_name or "Unknown Meal",
                "description": _generate_meal_description(meal),
                "meal_type": meal_type,
                "calories": meal.nutrition.total_calories if meal.nutrition else 0,
                "macros": {
                    "protein": meal.nutrition.total_protein if meal.nutrition else 0,
                    "carbs": meal.nutrition.total_carbohydrates if meal.nutrition else 0,
                    "fat": meal.nutrition.total_fat if meal.nutrition else 0,
                    "fiber": meal.nutrition.total_fiber if meal.nutrition else 0,
                    "sugar": meal.nutrition.total_sugar if meal.nutrition else 0,
                    "sodium": meal.nutrition.total_sodium if meal.nutrition else 0,
                },
                "quantity": meal.weight_grams if meal.weight_grams else 100,
                "status": meal.status.value if meal.status else "unknown"
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

def _generate_meal_description(meal):
    """Generate a description for the meal activity."""
    if not meal:
        return "Meal"
    
    description_parts = []
    
    if meal.weight_grams:
        description_parts.append(f"{meal.weight_grams}g")
    
    if meal.nutrition and meal.nutrition.total_calories:
        description_parts.append(f"{int(meal.nutrition.total_calories)} calories")
    
    if meal.meal_name and "," in meal.meal_name:
        # If meal name contains ingredients, use first part
        main_item = meal.meal_name.split(",")[0].strip()
        description_parts.insert(0, main_item)
    
    return " • ".join(description_parts) if description_parts else meal.meal_name or "Meal" 