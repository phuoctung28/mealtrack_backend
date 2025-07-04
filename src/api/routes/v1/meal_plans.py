from fastapi import APIRouter, HTTPException

from src.api.schemas.request import (
    ConversationMessageRequest,
    GenerateMealPlanRequest,
    ReplaceMealRequest
)
from src.api.schemas.response import (
    ConversationMessageResponse,
    StartConversationResponse,
    ConversationHistoryResponse,
    MealPlanResponse,
    ReplaceMealResponse
)
from src.app.handlers.meal_plan_handler import MealPlanHandler, ConversationHandler
from src.domain.services.conversation_service import ConversationService
from src.domain.services.meal_plan_service import MealPlanService

router = APIRouter(prefix="/v1/meal-plans", tags=["Meal Planning"])

# Initialize services and handlers
meal_plan_service = MealPlanService()
conversation_service = ConversationService(meal_plan_service)
meal_plan_handler = MealPlanHandler(meal_plan_service)
conversation_handler = ConversationHandler(conversation_service)


# Conversation endpoints
@router.post("/conversations/start", response_model=StartConversationResponse)
async def start_conversation(user_id: str = "default_user"):
    """Start a new meal planning conversation"""
    result = conversation_handler.start_conversation(user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return StartConversationResponse(
        conversation_id=result["conversation_id"],
        state=result["state"],
        assistant_message=result["assistant_message"]
    )


@router.post("/conversations/{conversation_id}/messages", response_model=ConversationMessageResponse)
async def send_message(conversation_id: str, request: ConversationMessageRequest):
    """Send a message to the meal planning assistant"""
    result = conversation_handler.process_message(
        conversation_id=conversation_id,
        user_message=request.message
    )
    
    if not result["success"]:
        raise HTTPException(status_code=404 if result["error"] == "Conversation not found" else 500, 
                          detail=result["message"])
    
    return ConversationMessageResponse(
        conversation_id=conversation_id,
        state=result["state"],
        assistant_message=result["assistant_message"],
        requires_input=result["requires_input"],
        meal_plan_id=result.get("meal_plan_id")
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    result = conversation_handler.get_conversation_history(conversation_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    conversation_data = result["conversation"]
    return ConversationHistoryResponse(**conversation_data)


# Direct meal plan generation endpoints
@router.post("/generate", response_model=MealPlanResponse)
async def generate_meal_plan(request: GenerateMealPlanRequest, user_id: str = "default_user"):
    """Generate a meal plan directly without conversation"""
    result = meal_plan_handler.generate_meal_plan(
        user_id=user_id,
        preferences=request.preferences
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    meal_plan_data = result["meal_plan"]
    return MealPlanResponse(**meal_plan_data)


@router.get("/{plan_id}", response_model=MealPlanResponse)
async def get_meal_plan(plan_id: str):
    """Get an existing meal plan"""
    result = meal_plan_handler.get_meal_plan(plan_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return MealPlanResponse(**result["meal_plan"])


@router.post("/{plan_id}/meals/replace", response_model=ReplaceMealResponse)
async def replace_meal(plan_id: str, request: ReplaceMealRequest):
    """Replace a specific meal in a plan"""
    result = meal_plan_handler.regenerate_meal(
        plan_id=plan_id,
        date=request.date,
        meal_id=request.meal_id,
        additional_preferences={
            "dietary_preferences": request.dietary_preferences,
            "exclude_ingredients": request.exclude_ingredients,
            "preferred_cuisine": request.preferred_cuisine
        }
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return ReplaceMealResponse(
        success=True,
        new_meal=result["new_meal"],
        message="Meal replaced successfully"
    )


# Health check for meal planning
@router.get("/health")
async def meal_plan_health():
    """Check if meal planning service is healthy"""
    return {
        "status": "healthy",
        "service": "meal_planning",
        "features": [
            "conversational_planning",
            "direct_generation",
            "meal_replacement"
        ]
    }