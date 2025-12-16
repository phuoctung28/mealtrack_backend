"""
Meal suggestion API endpoints.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request import (
    MealSuggestionRequest,
    SaveMealSuggestionRequest
)
from src.api.schemas.response import (
    MealSuggestionsResponse,
    SaveMealSuggestionResponse
)
from src.app.commands.meal_suggestion import (
    GenerateMealSuggestionsCommand,
    SaveMealSuggestionCommand
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-suggestions", tags=["Meal Suggestions"])


@router.post("/generate", response_model=MealSuggestionsResponse)
async def generate_meal_suggestions(
    request: MealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Generate exactly 3 meal suggestions based on user inputs.
    
    This endpoint generates 3 meal suggestions for a specific meal type based on:
    - Available ingredients (optional)
    - Time constraints (optional)
    - Dietary preferences (optional)
    - Calorie targets (optional)
    
    The system can also regenerate suggestions by excluding previously suggested meals.
    
    Authentication required: User ID is automatically extracted from the Firebase token.
    
    Parameters:
    - meal_type: Type of meal (breakfast, lunch, dinner, snack) - REQUIRED
    - ingredients: List of available ingredients (max 20) - OPTIONAL
    - time_available_minutes: Time constraint in minutes - OPTIONAL
    - dietary_preferences: Dietary preferences (e.g., vegetarian, vegan) - OPTIONAL
    - calorie_target: Target calories for the meal - OPTIONAL
    - exclude_ids: List of meal IDs to exclude (for regeneration) - OPTIONAL
    
    Returns:
    - request_id: Unique identifier for this request
    - suggestions: List of exactly 3 meal suggestions
    - generation_token: Token for tracking regeneration
    """
    try:
        # Create command
        command = GenerateMealSuggestionsCommand(
            user_id=user_id,
            meal_type=request.meal_type,
            ingredients=request.ingredients,
            time_available_minutes=request.time_available_minutes,
            dietary_preferences=request.dietary_preferences,
            calorie_target=request.calorie_target,
            exclude_ids=request.exclude_ids
        )
        
        # Execute the command
        result = await event_bus.send(command)
        
        # Return response
        return MealSuggestionsResponse(**result)
        
    except Exception as e:
        raise handle_exception(e) from e


@router.post("/save", response_model=SaveMealSuggestionResponse)
async def save_meal_suggestion(
    request: SaveMealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Save a selected meal suggestion to the user's meal history.
    
    This endpoint saves a meal suggestion to the user's planned meals for a specific date.
    The meal can then be viewed in the user's meal plan and tracked in their daily nutrition.
    
    Authentication required: User ID is automatically extracted from the Firebase token.
    
    Parameters:
    - suggestion_id: ID of the suggestion to save - REQUIRED
    - name: Name of the meal - REQUIRED
    - description: Description of the meal - OPTIONAL
    - meal_type: Type of meal (breakfast, lunch, dinner, snack) - REQUIRED
    - estimated_cook_time_minutes: Total cooking time - REQUIRED
    - calories: Calories for the meal - REQUIRED
    - protein: Protein in grams - REQUIRED
    - carbs: Carbohydrates in grams - REQUIRED
    - fat: Fat in grams - REQUIRED
    - ingredients_list: List of ingredients - OPTIONAL
    - instructions: Cooking instructions - OPTIONAL
    - meal_date: Date to save the meal for (YYYY-MM-DD), defaults to today - OPTIONAL
    
    Returns:
    - success: Whether the save was successful
    - message: Status message
    - meal_id: ID of the saved meal in the database
    - meal_date: Date the meal was saved for
    """
    try:
        # Parse meal date if provided
        meal_date = None
        if request.meal_date:
            try:
                meal_date = datetime.strptime(request.meal_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("meal_date must be in YYYY-MM-DD format")
        else:
            meal_date = date.today()
        
        # Create command
        command = SaveMealSuggestionCommand(
            user_id=user_id,
            suggestion_id=request.suggestion_id,
            name=request.name,
            description=request.description,
            meal_type=request.meal_type,
            estimated_cook_time_minutes=request.estimated_cook_time_minutes,
            calories=request.calories,
            protein=request.protein,
            carbs=request.carbs,
            fat=request.fat,
            ingredients_list=request.ingredients_list,
            instructions=request.instructions,
            meal_date=meal_date
        )
        
        # Execute the command
        result = await event_bus.send(command)
        
        # Return response
        return SaveMealSuggestionResponse(**result)
        
    except Exception as e:
        raise handle_exception(e) from e

