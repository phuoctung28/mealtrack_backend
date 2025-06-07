from fastapi import APIRouter, UploadFile, HTTPException, status, Depends, File, BackgroundTasks, Query
from typing import Dict, List
from api.dependencies import get_upload_meal_image_handler, get_meal_handler
from app.handlers.upload_meal_image_handler import UploadMealImageHandler
from app.handlers.meal_handler import MealHandler
from api.schemas.meal_schemas import (
    CreateMealRequest, UpdateMealRequest, UpdateMealMacrosRequest,
    MealResponse, MealPhotoResponse, PaginatedMealResponse,
    MealSearchRequest, MealSearchResponse, MealStatusResponse,
    DetailedMealResponse, MacrosSchema
)
from domain.model.meal import MealStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/meals",
    tags=["meals"],
)

MAX_FILE_SIZE = 8 * 1024 * 1024

ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png"]

@router.post("/image", status_code=status.HTTP_201_CREATED, response_model=Dict)
async def upload_meal_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler),
):
    """
    Send meal photo and return meal analysis with nutritional data.
    
    - Accepts image/jpeg or image/png files up to 8MB
    - Returns meal identification and nutritional analysis
    - Must priority endpoint for meal scanning
    """
    try:
        # Validate content type
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Only {', '.join(ALLOWED_CONTENT_TYPES)} are allowed."
            )
        
        # Read file content
        contents = await file.read()
        
        # Validate file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed (8MB)"
            )
        
        # Process the upload using the application handler
        logger.info("Analyzing meal photo")
        result = handler.handle(contents, file.content_type)
        logger.info(f"Meal created with ID: {result.meal_id}")
        
        if background_tasks:
            logger.info(f"Adding background task to analyze meal {result.meal_id}")
            background_tasks.add_task(handler.analyze_meal_background, result.meal_id)
        
        return {
            "meal_id": result.meal_id,
            "status": result.status
        }

    except Exception as e:
        logger.error(f"Error analyzing meal photo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing meal photo: {str(e)}"
        )

@router.get("/{meal_id}", response_model=DetailedMealResponse)
async def get_meal(
    meal_id: str,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """
    Retrieve meal information by its id.
    - Returns complete meal information including nutritional data
    """
    meal = meal_handler.get_meal(meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail=f"Meal with ID {meal_id} not found")
    
    return DetailedMealResponse.from_domain(meal)

@router.put("/{meal_id}", response_model=MealResponse)
async def update_meal(
    meal_id: str,
    meal_data: UpdateMealRequest,
    # handler: MealHandler = Depends(get_meal_handler)
):
    """
    Update meal info and macros.
    
    - Updates existing meal item
    - Must priority endpoint for meal modification
    """
    try:
        # TODO: Implement meal update
        logger.info(f"Updating meal: {meal_id}")
        
        # Placeholder response - implement actual update
        return MealResponse(
            meal_id=meal_id,
            name=meal_data.name or "Updated Meal",
            description=meal_data.description,
            serving_size=meal_data.serving_size,
            serving_unit=meal_data.serving_unit,
            calories_per_serving=meal_data.calories_per_serving,
            macros_per_serving=meal_data.macros_per_serving,
            status="updated",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T12:00:00Z"
        )
        
    except Exception as e:
        logger.error(f"Error updating meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating meal: {str(e)}"
        )

@router.get("/", response_model=PaginatedMealResponse)
async def list_meals(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # handler: MealHandler = Depends(get_meal_handler)
):
    """
    Get paginated list of meals.
    
    - Returns paginated meal data
    - Should priority endpoint for meal browsing
    """
    try:
        # TODO: Implement paginated meal retrieval
        logger.info(f"Fetching meals - page: {page}, page_size: {page_size}")
        
        # Placeholder response - implement actual pagination
        sample_meals = []
        for i in range(min(page_size, 5)):  # Return up to 5 sample meals
            sample_meals.append(MealResponse(
                meal_id=f"meal-{i+1}",
                name=f"Sample Meal {i+1}",
                description=f"Description for meal {i+1}",
                status="ready",
                created_at="2024-01-01T00:00:00Z"
            ))
        
        return PaginatedMealResponse(
            meals=sample_meals,
            total=50,  # Placeholder total
            page=page,
            page_size=page_size,
            total_pages=(50 + page_size - 1) // page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing meals: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing meals: {str(e)}"
        )

@router.post("/{meal_id}/macros", response_model=MealResponse)
async def update_meal_macros(
    meal_id: str,
    macros_request: UpdateMealMacrosRequest,
    background_tasks: BackgroundTasks,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """
    Send size and/or amount of food to update food macros.
    
    - Updates meal macros based on portion size or amount
    - Triggers LLM-based nutrition recalculation for accuracy
    - Must priority endpoint for portion adjustment
    """
    try:
        logger.info(f"Updating macros for meal {meal_id} with size: {macros_request.size}, amount: {macros_request.amount}, unit: {macros_request.unit}")
        
        # Get the current meal
        meal = meal_handler.get_meal(meal_id)
        if not meal:
            raise HTTPException(status_code=404, detail=f"Meal with ID {meal_id} not found")
        
        # Calculate new serving size
        new_amount = macros_request.size or macros_request.amount
        if not new_amount:
            raise HTTPException(status_code=400, detail="Either size or amount must be provided")
        
        # Store the portion adjustment information
        # In a real implementation, you would:
        # 1. Update the meal's serving size in the database
        # 2. Trigger LLM recalculation with the new portion size
        # 3. Use the original image but with portion size context
        
        # For now, we'll mark the meal for re-analysis with portion context
        logger.info(f"Triggering LLM recalculation for meal {meal_id} with new portion: {new_amount}{macros_request.unit or 'g'}")
        
        # Add background task to re-analyze with new portion size
        # This would call the LLM with additional context about portion size
        from api.dependencies import get_upload_meal_image_handler
        handler = get_upload_meal_image_handler()
        
        # Schedule background re-analysis with portion context
        background_tasks.add_task(
            _recalculate_meal_with_portion,
            meal_id,
            new_amount,
            macros_request.unit or "g",
            handler
        )
        
        # Calculate temporary proportional macros for immediate response
        # (The LLM will provide more accurate results asynchronously)
        base_serving_size = meal.nutrition.food_items[0].quantity if meal.nutrition and meal.nutrition.food_items else 100.0
        ratio = new_amount / base_serving_size
        
        # Get current macros and scale them
        current_macros = meal.nutrition.macros if meal.nutrition else MacrosSchema(protein=20.0, carbs=30.0, fat=10.0, fiber=5.0)
        current_calories = meal.nutrition.calories if meal.nutrition else 250.0
        
        updated_macros = MacrosSchema(
            protein=round(current_macros.protein * ratio, 1),
            carbs=round(current_macros.carbs * ratio, 1),
            fat=round(current_macros.fat * ratio, 1),
            fiber=round(current_macros.fiber * ratio, 1) if current_macros.fiber else None
        )
        
        updated_calories = round(current_calories * ratio, 1)
        
        logger.info(f"Immediate response with scaled macros for {new_amount}{macros_request.unit or 'g'}: {updated_macros.protein}p, {updated_macros.carbs}c, {updated_macros.fat}f")
        logger.info(f"LLM recalculation scheduled in background for more accurate results")
        
        # Return immediate response with scaled macros
        # Note: User should check meal status later for LLM-calculated results
        return MealResponse(
            meal_id=meal_id,
            name=meal.name if hasattr(meal, 'name') else "Meal",
            description=f"Portion adjusted to {new_amount}{macros_request.unit or 'g'} - LLM recalculation in progress",
            serving_size=new_amount,
            serving_unit=macros_request.unit or "g",
            calories_per_serving=updated_calories,
            macros_per_serving=updated_macros,
            status="analyzing",  # Indicates LLM recalculation in progress
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T12:00:00Z"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating macros for meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating meal macros: {str(e)}"
        )

def _recalculate_meal_with_portion(meal_id: str, portion_size: float, unit: str, handler):
    """
    Background task to recalculate meal nutrition with new portion size using LLM.
    
    Args:
        meal_id: ID of the meal to recalculate
        portion_size: New portion size
        unit: Unit of the portion size
        handler: Upload meal image handler with LLM integration
    """
    try:
        logger.info(f"Background task: Recalculating meal {meal_id} with portion {portion_size}{unit}")
        
        # Use the specialized portion-aware analysis method
        handler.analyze_meal_with_portion_background(meal_id, portion_size, unit)
        
        logger.info(f"Background task: Completed recalculation for meal {meal_id}")
        
    except Exception as e:
        logger.error(f"Background task: Error recalculating meal {meal_id}: {str(e)}", exc_info=True)

@router.get("/{meal_id}/status", response_model=MealStatusResponse)
async def get_meal_status(
    meal_id: str,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """
    Get only the status of a meal.
    
    This is a lightweight endpoint that returns just the status without
    the full meal details.
    """
    meal = meal_handler.get_meal(meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail=f"Meal with ID {meal_id} not found")
    
    return MealStatusResponse(
        meal_id=meal.meal_id,
        status=meal.status.value,
        status_message=_get_status_message(meal.status),
        error_message=meal.error_message
    )

def _get_status_message(status: MealStatus) -> str:
    """Get a user-friendly status message based on the meal status."""
    messages = {
        MealStatus.PROCESSING: "Your meal is being processed",
        MealStatus.ANALYZING: "AI is analyzing your meal",
        MealStatus.ENRICHING: "Enhancing your meal data",
        MealStatus.READY: "Your meal analysis is ready",
        MealStatus.FAILED: "Analysis failed"
    }
    return messages.get(status, "Unknown status") 