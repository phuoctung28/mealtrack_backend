from fastapi import APIRouter, UploadFile, HTTPException, status, Depends, File, BackgroundTasks
from typing import Dict
from api.dependencies import get_upload_meal_image_handler, get_meal_handler
from app.handlers.upload_meal_image_handler import UploadMealImageHandler
from app.handlers.meal_handler import MealHandler
from api.schemas.meal_response import MealResponse, MealStatusResponse
from domain.model.meal import MealStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/meals",
    tags=["meals"],
)

# Maximum file size (8 MB)
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB in bytes

# Allowed content types
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png"]

@router.post("/image", status_code=status.HTTP_201_CREATED, response_model=Dict)
async def upload_meal_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler),
):
    """
    Upload a meal image for analysis.
    
    - Accepts image/jpeg or image/png files up to 8MB
    - Returns meal ID and processing status
    - Analysis will run automatically in the background
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
        logger.info("Handling meal upload")
        result = handler.handle(contents, file.content_type)
        logger.info(f"Meal created with ID: {result.meal_id}")
        
        # Add background task to analyze the meal
        if background_tasks:
            logger.info(f"Adding background task to analyze meal {result.meal_id}")
            background_tasks.add_task(handler.analyze_meal_background, result.meal_id)
        
        return {
            "meal_id": result.meal_id,
            "status": result.status
        }
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Error uploading meal image: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading meal image: {str(e)}"
        )

@router.get("/{meal_id}", response_model=MealResponse)
async def get_meal(
    meal_id: str,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """
    Get meal details by ID.
    
    This endpoint implements US-2.3 - Check meal status.
    
    Args:
        meal_id: ID of the meal to retrieve
        meal_handler: Meal handler dependency
        
    Returns:
        Meal details including status and nutrition if available
        
    Raises:
        HTTPException: If meal is not found
    """
    meal = meal_handler.get_meal(meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail=f"Meal with ID {meal_id} not found")
    
    return MealResponse.from_domain(meal)

@router.get("/{meal_id}/status", response_model=MealStatusResponse)
async def get_meal_status(
    meal_id: str,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """
    Get only the status of a meal.
    
    This is a lightweight endpoint that returns just the status without
    the full meal details.
    
    Args:
        meal_id: ID of the meal to check
        meal_handler: Meal handler dependency
        
    Returns:
        Current status of the meal
        
    Raises:
        HTTPException: If meal is not found
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