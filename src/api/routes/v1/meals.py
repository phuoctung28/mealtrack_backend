import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, UploadFile, HTTPException, status, Depends, File, BackgroundTasks

from src.api.dependencies import get_upload_meal_image_handler, get_meal_handler
from src.api.mappers.meal_mapper import MealMapper
from src.api.schemas.request import UpdateMealMacrosRequest
from src.api.schemas.response import (
    DetailedMealResponse,
    MealStatusResponse
)
from src.app.handlers.meal_handler import MealHandler
from src.app.handlers.upload_meal_image_handler import UploadMealImageHandler
from src.domain.model.meal import MealStatus, Meal

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/meals",
    tags=["meals"],
)

MAX_FILE_SIZE = 8 * 1024 * 1024

ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/jpg", "image/png"]

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

@router.post("/image/analyze", status_code=status.HTTP_200_OK, response_model=DetailedMealResponse)
async def analyze_meal_image_immediate(
    file: UploadFile = File(...),
    handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler),
):
    """
    Send meal photo and return immediate meal analysis with nutritional data.
    
    This endpoint processes the image and returns complete nutritional analysis
    synchronously without background processing. Use this when you need 
    immediate results.
    
    - Accepts image/jpeg or image/png files up to 8MB
    - Returns complete meal analysis immediately
    - Processing time may be longer than the background version
    - Recommended for interactive use cases
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
        
        # Process the upload and analyze immediately
        logger.info("Analyzing meal photo immediately")
        meal = handler.handle_immediate(contents, file.content_type)
        logger.info(f"Immediate analysis completed for meal ID: {meal.meal_id}, status: {meal.status}")
        
        # Check if analysis was successful
        if meal.status.value == "FAILED":
            error_message = meal.error_message or "Analysis failed"
            logger.error(f"Immediate analysis failed: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to analyze meal image: {error_message}"
            )
        
        # Return the detailed meal response using mapper
        return MealMapper.to_detailed_response(meal)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in immediate meal analysis: {str(e)}", exc_info=True)
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
    
    return MealMapper.to_detailed_response(meal)

@router.post("/{meal_id}/macros", response_model=DetailedMealResponse)
async def update_meal_macros(
    meal_id: str,
    macros_request: UpdateMealMacrosRequest,
    background_tasks: BackgroundTasks,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """
    Update meal macros based on actual weight in grams.
    
    - Updates meal macros based on precise weight measurement
    - Triggers LLM-based nutrition recalculation for accuracy
    - Must priority endpoint for portion adjustment
    """
    try:
        logger.info(f"Updating macros for meal {meal_id} with weight: {macros_request.weight_grams}g")
        
        # Get the current meal
        meal = meal_handler.get_meal(meal_id)
        if not meal:
            raise HTTPException(status_code=404, detail=f"Meal with ID {meal_id} not found")
        
        # Validate weight
        new_weight_grams = macros_request.weight_grams
        
        # Update the meal with new weight and persist the changes
        updated_meal = meal_handler.update_meal_weight(meal_id, new_weight_grams)
        if not updated_meal:
            raise HTTPException(status_code=404, detail=f"Failed to update meal {meal_id}")
        
        logger.info(f"Successfully updated meal {meal_id} weight to {new_weight_grams}g in database")
        
        # Add background task to re-analyze with new weight
        # This would call the LLM with additional context about weight
        from src.api.dependencies import get_upload_meal_image_handler
        handler = get_upload_meal_image_handler()
        
        # Schedule background re-analysis with weight context
        background_tasks.add_task(
            _recalculate_meal_with_weight,
            meal_id,
            new_weight_grams,
            handler
        )
        
        # Calculate temporary proportional macros for immediate response
        # (The LLM will provide more accurate results asynchronously)
        base_weight = getattr(updated_meal, 'original_weight_grams', 300.0)
        ratio = new_weight_grams / base_weight
        
        # Get current macros and scale them
        current_macros = meal.nutrition.macros if meal.nutrition else MacrosSchema(protein=20.0, carbs=30.0, fat=10.0, fiber=5.0)
        current_calories = meal.nutrition.calories if meal.nutrition else 250.0
        
        # Calculate total macros for the new weight
        total_macros = MacrosSchema(
            protein=round(current_macros.protein * ratio, 1),
            carbs=round(current_macros.carbs * ratio, 1),
            fat=round(current_macros.fat * ratio, 1),
            fiber=round(current_macros.fiber * ratio, 1) if current_macros.fiber else None
        )
        
        total_calories = round(current_calories * ratio, 1)
        
        # Calculate per-100g values
        weight_ratio_for_100g = new_weight_grams / 100.0
        calories_per_100g = round(total_calories / weight_ratio_for_100g, 1)
        macros_per_100g = MacrosSchema(
            protein=round(total_macros.protein / weight_ratio_for_100g, 1),
            carbs=round(total_macros.carbs / weight_ratio_for_100g, 1),
            fat=round(total_macros.fat / weight_ratio_for_100g, 1),
            fiber=round(total_macros.fiber / weight_ratio_for_100g, 1) if total_macros.fiber else None
        )
        
        logger.info(f"Calculated macros for {new_weight_grams}g: {total_macros.protein}p, {total_macros.carbs}c, {total_macros.fat}f")
        logger.info(f"LLM recalculation scheduled in background for more accurate results")
        
        # Return response with the updated meal data using mapper
        return MealMapper.to_detailed_response(updated_meal)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating macros for meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating meal macros: {str(e)}"
        )

def _recalculate_meal_with_weight(meal_id: str, weight_grams: float, handler):
    """
    Background task to recalculate meal nutrition with new weight using LLM.
    
    Args:
        meal_id: ID of the meal to recalculate
        weight_grams: New weight in grams
        handler: Upload meal image handler with LLM integration
    """
    try:
        logger.info(f"Background task: Recalculating meal {meal_id} with weight {weight_grams}g using LLM")
        
        # Use the specialized weight-aware analysis method
        handler.analyze_meal_with_weight_background(meal_id, weight_grams)
        
        logger.info(f"Background task: LLM recalculation completed for meal {meal_id}")
        
    except Exception as e:
        logger.error(f"Background task: Error recalculating meal {meal_id} with LLM: {str(e)}", exc_info=True)
        
        # Try to mark meal as failed
        try:
            from src.api.dependencies import get_meal_handler
            meal_handler = get_meal_handler()
            meal = meal_handler.get_meal(meal_id)
            if meal:
                # Update meal to failed status
                failed_meal = Meal(
                    meal_id=meal.meal_id,
                    status=MealStatus.FAILED,
                    created_at=meal.created_at,
                    updated_at=datetime.now(),
                    image=meal.image,
                    dish_name=meal.dish_name,
                    nutrition=meal.nutrition,
                    error_message=f"LLM recalculation failed: {str(e)}"
                )
                meal_handler.meal_repository.save(failed_meal)
        except Exception as mark_failed_error:
            logger.error(f"Background task: Error marking meal as failed: {str(mark_failed_error)}")

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