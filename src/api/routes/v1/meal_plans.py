"""
Meal planning API endpoints - Event-driven architecture.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request import (
    IngredientBasedMealPlanRequest
)
from src.api.schemas.response import (
    MealsByDateResponse,
    MealPlanGenerationStatusResponse
)
from src.app.commands.meal_plan import (
    GenerateWeeklyIngredientBasedMealPlanCommand,
)
from src.app.queries.meal_plan import (
    GetMealPlanQuery,
    GetMealsByDateQuery
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-plans", tags=["Meal Planning"])


@router.post("/generate/weekly-ingredient-based", response_model=MealPlanGenerationStatusResponse)
async def generate_weekly_ingredient_based_meal_plan(
    user_id: str,
    request: IngredientBasedMealPlanRequest,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Generate a weekly meal plan based on provided ingredients and user preferences.
    
    This endpoint generates a comprehensive weekly meal plan using the ingredients provided
    in the request body, combined with the user's profile, preferences, and goals.
    
    The system generates the meal plan in the background and returns a simple success status,
    allowing the frontend to show a loading screen and navigate to the home screen once complete.
    """
    try:
        # Generate weekly meal plan using ingredients from request
        command = GenerateWeeklyIngredientBasedMealPlanCommand(
            user_id=user_id,
            available_ingredients=request.available_ingredients,
            available_seasonings=request.available_seasonings
        )
        
        # Execute the command - this generates the full meal plan and saves it to the database
        await event_bus.send(command)
        
        # Return simple status response instead of full meal plan data
        return MealPlanGenerationStatusResponse(
            success=True,
            message="Weekly meal plan generated successfully!",
            user_id=user_id
        )
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/{plan_id}")
async def get_meal_plan(
    plan_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Get an existing meal plan."""
    try:
        # Create query
        query = GetMealPlanQuery(plan_id=plan_id)
        
        # Send query
        result = await event_bus.send(query)
        
        return result["meal_plan"]
    except Exception as e:
        raise handle_exception(e)


# Query meals by date
@router.get("/meals/by-date", response_model=MealsByDateResponse)
async def get_meals_by_date(
    user_id: str,
    meal_date: date = Query(..., description="Date to get meals for (YYYY-MM-DD format)"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get meals for a specific date.
    
    Retrieves all meals planned for the specified date. Can optionally filter by meal type.
    This endpoint searches through all stored meal plans (both daily and weekly) to find
    meals that match the requested date.
    
    Parameters:
    - user_id: The user to get meals for
    - meal_date: The specific date to retrieve meals for (YYYY-MM-DD format)
    - meal_type: Optional filter to only return specific meal type (breakfast, lunch, dinner, snack)
    """
    try:
        # Create query
        query = GetMealsByDateQuery(
            user_id=user_id,
            meal_date=meal_date,
        )
        
        # Send query
        result = await event_bus.send(query)
        
        return MealsByDateResponse(**result)
    except Exception as e:
        raise handle_exception(e)