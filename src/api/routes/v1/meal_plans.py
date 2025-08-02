"""
Meal planning API endpoints - Event-driven architecture.
"""
from fastapi import APIRouter, Depends

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
    WeeklyMealPlanResponse
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
    GetMealPlanQuery
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


@router.post("/generate/ingredient-based", response_model=DailyMealPlanResponse)
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
        
        return DailyMealPlanResponse(**result)
        
    except Exception as e:
        raise handle_exception(e)


@router.post("/generate/weekly-ingredient-based", response_model=WeeklyMealPlanResponse)
async def generate_weekly_ingredient_based_meal_plan(
    request: IngredientBasedMealPlanRequest,
    user_id: str = "default_user",
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Generate a weekly meal plan (Monday to Sunday) based on available ingredients and seasonings.
    
    This endpoint creates comprehensive weekly meal plans using only the ingredients you have available,
    helping to minimize food waste and maximize ingredient utilization across the entire week.
    
    The system generates all meals for the week in a single LLM call, ensuring better meal coordination
    and variety across the week.
    """
    try:
        available_ingredients = request.available_ingredients
        
        command = GenerateWeeklyIngredientBasedMealPlanCommand(
            user_id=user_id,
            available_ingredients=available_ingredients,
            available_seasonings=request.available_seasonings
        )
        
        result = await event_bus.send(command)
        
        return WeeklyMealPlanResponse(**result)
        
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
            "meal_replacement"
        ]
    }