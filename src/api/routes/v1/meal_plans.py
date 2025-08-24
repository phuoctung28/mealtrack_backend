"""
Meal planning API endpoints - Event-driven architecture.
"""
from fastapi import APIRouter, Depends, Query
from datetime import date

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request import (
    ConversationMessageRequest,
    ReplaceMealRequest,
    IngredientBasedMealPlanRequest
)
from src.api.schemas.response import (
    ConversationMessageResponse,
    StartConversationResponse,
    ConversationHistoryResponse,
    ReplaceMealResponse,
    DailyMealPlanResponse,
    DailyMealPlanStrongResponse,
    WeeklyMealPlanResponse,
    MealsByDateResponse,
    MealPlanGenerationStatusResponse
)
from src.app.commands.meal_plan import (
    StartMealPlanConversationCommand,
    SendConversationMessageCommand,
    GenerateDailyMealPlanCommand,
    GenerateIngredientBasedMealPlanCommand,
    GenerateWeeklyIngredientBasedMealPlanCommand,
    ReplaceMealInPlanCommand
)
from src.app.queries.meal_plan import (
    GetConversationHistoryQuery,
    GetMealPlanQuery,
    GetMealsByDateQuery
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-plans", tags=["Meal Planning"])


# Conversation endpoints
@router.post("/conversations/start", response_model=StartConversationResponse)
async def start_conversation(
    user_id: str = "default_user",
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Start a new meal planning conversation."""
    try:
        # Create command
        command = StartMealPlanConversationCommand(user_id=user_id)
        
        # Send command
        result = await event_bus.send(command)
        
        return StartConversationResponse(
            conversation_id=result["conversation_id"],
            state=result["state"],
            assistant_message=result["assistant_message"]
        )
    except Exception as e:
        raise handle_exception(e)


@router.post("/conversations/{conversation_id}/messages", response_model=ConversationMessageResponse)
async def send_message(
    conversation_id: str,
    request: ConversationMessageRequest,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Send a message to the meal planning assistant."""
    try:
        # Create command
        command = SendConversationMessageCommand(
            conversation_id=conversation_id,
            message=request.message
        )
        
        # Send command
        result = await event_bus.send(command)
        
        return ConversationMessageResponse(
            conversation_id=conversation_id,
            state=result["state"],
            assistant_message=result["assistant_message"],
            requires_input=result["requires_input"],
            meal_plan_id=result.get("meal_plan_id")
        )
    except Exception as e:
        raise handle_exception(e)


@router.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation(
    conversation_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Get conversation history."""
    try:
        # Create query
        query = GetConversationHistoryQuery(conversation_id=conversation_id)
        
        # Send query
        result = await event_bus.send(query)
        
        conversation_data = result["conversation"]
        return ConversationHistoryResponse(**conversation_data)
    except Exception as e:
        raise handle_exception(e)


# Direct meal plan generation endpoints
@router.post("/generate/daily", response_model=DailyMealPlanResponse)
async def generate_daily_meal_plan(
    user_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Generate a daily meal plan based on user profile.
    
    Uses the user's stored profile including:
    - Physical attributes (age, gender, height, weight)
    - Dietary preferences and restrictions
    - Health conditions and allergies
    - Fitness goals and activity level
    - Meal preferences (meals per day, snacks per day)
    
    Automatically calculates TDEE and macro targets, then generates
    personalized meal suggestions for the day.
    """
    try:
        # Create command
        command = GenerateDailyMealPlanCommand(user_id=user_id)
        
        # Send command
        result = await event_bus.send(command)
        
        return DailyMealPlanResponse(**result)
    except Exception as e:
        raise handle_exception(e)


@router.post("/generate/ingredient-based", response_model=DailyMealPlanStrongResponse)
async def generate_ingredient_based_meal_plan(
    request: IngredientBasedMealPlanRequest,
    user_id: str = "default_user",
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Generate a daily meal plan based on available ingredients and seasonings.
    
    This endpoint creates comprehensive meal plans using only the ingredients you have available,
    helping to minimize food waste and maximize ingredient utilization across the entire day.
    """
    try:
        available_ingredients = request.available_ingredients
        
        command = GenerateIngredientBasedMealPlanCommand(
            user_id=user_id,
            available_ingredients=available_ingredients,
            available_seasonings=request.available_seasonings
        )
        
        result = await event_bus.send(command)
        
        return result
        
    except Exception as e:
        raise handle_exception(e)


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


@router.post("/{plan_id}/meals/replace", response_model=ReplaceMealResponse)
async def replace_meal(
    plan_id: str,
    request: ReplaceMealRequest,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Replace a specific meal in a plan."""
    try:
        # Create command
        command = ReplaceMealInPlanCommand(
            plan_id=plan_id,
            date=request.date,
            meal_id=request.meal_id,
            dietary_preferences=request.dietary_preferences,
            exclude_ingredients=request.exclude_ingredients,
            preferred_cuisine=request.preferred_cuisine
        )
        
        # Send command
        result = await event_bus.send(command)
        
        return ReplaceMealResponse(
            success=True,
            new_meal=result["new_meal"],
            message="Meal replaced successfully"
        )
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


# Health check for meal planning
@router.get("/health")
async def meal_plan_health():
    """Check if meal planning service is healthy."""
    return {
        "status": "healthy",
        "service": "meal_planning",
        "features": [
            "conversational_planning",
            "direct_generation",
            "meal_replacement",
            "date_query"
        ]
    }