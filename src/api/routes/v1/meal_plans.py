"""
Meal planning API endpoints - Event-driven architecture.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request import (
    IngredientBasedMealPlanRequest
)
from src.api.schemas.response import (
    MealsByDateResponse,
    MealPlanGenerationStatusResponse
)
from src.api.schemas.response.task_responses import TaskCreatedResponse
from src.app.commands.meal_plan import (
    GenerateWeeklyIngredientBasedMealPlanCommand,
)
from src.app.queries.meal_plan import (
    GetMealPlanQuery,
    GetMealsFromPlanByDateQuery
)
from src.infra.event_bus import EventBus
from src.infra.rq.queue import get_queue
from src.infra.tasks.meal_plan_tasks import (
    generate_weekly_ingredient_based_meal_plan_task,
)

router = APIRouter(prefix="/v1/meal-plans", tags=["Meal Planning"])


@router.post("/generate/weekly-ingredient-based", response_model=MealPlanGenerationStatusResponse)
async def generate_weekly_ingredient_based_meal_plan(
    request: IngredientBasedMealPlanRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Generate a weekly meal plan based on provided ingredients and user preferences.
    
    This endpoint generates a comprehensive weekly meal plan using the ingredients provided
    in the request body, combined with the user's profile, preferences, and goals.
    
    The system generates the meal plan in the background and returns a simple success status,
    allowing the frontend to show a loading screen and navigate to the home screen once complete.
    
    Authentication required: User ID is automatically extracted from the Firebase token.
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
        raise handle_exception(e) from e


@router.post(
    "/generate/weekly-ingredient-based/async",
    status_code=202,
    response_model=TaskCreatedResponse,
)
async def generate_weekly_ingredient_based_meal_plan_async(
    request: IngredientBasedMealPlanRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Enqueue weekly meal plan generation and return a task id for polling."""
    try:
        queue = get_queue("default")
        job = queue.enqueue(
            generate_weekly_ingredient_based_meal_plan_task,
            user_id=user_id,
            available_ingredients=request.available_ingredients,
            available_seasonings=request.available_seasonings,
            job_timeout=300,
            result_ttl=3600,
            failure_ttl=3600,
            meta={"user_id": user_id},
        )
        return TaskCreatedResponse(
            task_id=job.id,
            status="queued",
            poll_url=f"/v1/tasks/{job.id}",
            message="Weekly meal plan generation started",
        )
    except Exception as e:
        raise handle_exception(e) from e


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
        raise handle_exception(e) from e


# Query meals by date
@router.get("/meals/by-date", response_model=MealsByDateResponse)
async def get_meals_by_date(
    meal_date: date = Query(..., description="Date to get meals for (YYYY-MM-DD format)"),
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get meals for a specific date.
    
    Retrieves all meals planned for the specified date. Can optionally filter by meal type.
    This endpoint searches through all stored meal plans (both daily and weekly) to find
    meals that match the requested date.
    
    Authentication required: User ID is automatically extracted from the Firebase token.
    
    Parameters:
    - meal_date: The specific date to retrieve meals for (YYYY-MM-DD format)
    - meal_type: Optional filter to only return specific meal type (breakfast, lunch, dinner, snack)
    """
    try:
        # Create query for planned meals by date
        query = GetMealsFromPlanByDateQuery(
            user_id=user_id,
            meal_date=meal_date,
        )

        # Send query - returns dict matching MealsByDateResponse
        result = await event_bus.send(query)

        return MealsByDateResponse(**result)
    except Exception as e:
        raise handle_exception(e) from e