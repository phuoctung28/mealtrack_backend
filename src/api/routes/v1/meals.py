"""
Meals API endpoints using event-driven architecture.
Clean separation with event bus pattern.
"""
import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query, BackgroundTasks, HTTPException, status

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.meal_mapper import MealMapper
from src.api.schemas.response import (
    DetailedMealResponse,
    MealListResponse
)
from src.api.schemas.response.daily_nutrition_response import DailyNutritionResponse
from src.api.schemas.response.meal_responses import MealStatusResponse
from src.api.utils.file_validator import FileValidator
from src.app.commands.meal import (
    UploadMealImageCommand,
    RecalculateMealNutritionCommand
)
from src.app.queries.meal import (
    GetMealByIdQuery,
    GetMealsByDateQuery,
    GetDailyMacrosQuery
)
from src.infra.event_bus import EventBus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/meals", tags=["Meals"])



# File upload constraints
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/jpg"]

# Status mapping from domain to API
STATUS_MAPPING = {
    "PROCESSING": "pending",
    "ANALYZING": "analyzing", 
    "ENRICHING": "analyzing",  # Map to analyzI mean ing since API doesn't have enriching
    "READY": "ready",
    "FAILED": "failed"
}


@router.post("/image", response_model=Dict[str, str])
async def upload_meal_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Upload and analyze a meal image.
    
    This endpoint:
    1. Validates the uploaded image
    2. Stores the image
    3. Creates a meal record
    4. Triggers background analysis (if background_tasks available)
    """
    try:
        # Validate file
        contents = await FileValidator.validate_image_file(
            file=file,
            allowed_content_types=ALLOWED_CONTENT_TYPES,
            max_size_bytes=MAX_FILE_SIZE
        )
        
        # Send upload command
        command = UploadMealImageCommand(
            file_contents=contents,
            content_type=file.content_type
        )
        
        result = await event_bus.send(command)
        
        # Background processing is handled by the event system
        # The MealImageUploadedEvent will trigger background analysis
        
        # Return a simple upload response
        return {
            "meal_id": result["meal_id"],
            "status": STATUS_MAPPING.get(result["status"], result["status"]),
            "message": "Meal image uploaded successfully"
        }
        
    except Exception as e:
        raise handle_exception(e)

@router.post("/image/analyze", status_code=status.HTTP_200_OK, response_model=DetailedMealResponse)
async def analyze_meal_image_immediate(
    file: UploadFile = File(...),
    event_bus: EventBus = Depends(get_configured_event_bus)
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
        
        # Process the upload and analysis immediately
        logger.info("Processing meal photo for immediate analysis")
        from src.app.commands.meal import UploadMealImageImmediatelyCommand
        
        command = UploadMealImageImmediatelyCommand(
            file_contents=contents,
            content_type=file.content_type
        )
        
        logger.info("Uploading and analyzing meal immediately")
        meal = await event_bus.send(command)
        
        logger.info(f"Immediate analysis completed for meal ID: {meal.meal_id}, status: {meal.status}")
        
        # Check if analysis was successful
        if meal.status.value == "FAILED":
            error_message = meal.error_message or "Analysis failed"
            logger.error(f"Immediate analysis failed: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to analyze meal image: {error_message}"
            )
        
        # Get the image URL if available
        image_url = None
        if meal.image:
            # Try to get URL from image store
            from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
            image_store = CloudinaryImageStore()
            image_url = image_store.get_url(meal.image.image_id)
        
        # Return the detailed meal response using mapper
        return MealMapper.to_detailed_response(meal, image_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in immediate meal analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing meal photo: {str(e)}"
        )


@router.get("/{meal_id}/status", response_model=MealStatusResponse)
async def get_meal_status(
    meal_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Get the processing status of a specific meal."""
    try:
        # Send query
        query = GetMealByIdQuery(meal_id=meal_id)
        meal = await event_bus.send(query)
        
        # Return lightweight status information
        return MealStatusResponse(
            meal_id=meal.meal_id,
            status=STATUS_MAPPING.get(meal.status.value, meal.status.value)
        )
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/{meal_id}", response_model=DetailedMealResponse)
async def get_meal(
    meal_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Get detailed information about a specific meal."""
    try:
        # Send query
        query = GetMealByIdQuery(meal_id=meal_id)
        meal = await event_bus.send(query)
        
        # Get image URL if available
        image_url = None
        if meal.image:
            from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
            image_store = CloudinaryImageStore()
            image_url = image_store.get_url(meal.image.image_id)
        
        # Use mapper to convert to response
        return MealMapper.to_detailed_response(meal, image_url)
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/daily/entries", response_model=MealListResponse)
async def get_daily_meal_entries(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Get all meal entries for a specific date."""
    try:
        # Parse date
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = datetime.now().date()
        
        # Send query
        query = GetMealsByDateQuery(target_date=target_date)
        meals = await event_bus.send(query)
        
        # Get image URLs if needed
        image_urls = {}
        for meal in meals:
            if meal.image:
                from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
                image_store = CloudinaryImageStore()
                image_urls[meal.meal_id] = image_store.get_url(meal.image.image_id)
        
        # Use mapper to convert to response
        return MealMapper.to_meal_list_response(
            meals=meals,
            total=len(meals),
            page=1,
            page_size=50,
            image_urls=image_urls
        )
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/daily/macros", response_model=DailyNutritionResponse)
async def get_daily_macros(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Get daily macronutrient summary for all meals."""
    try:
        # Parse date
        target_date = None
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Send query
        query = GetDailyMacrosQuery(target_date=target_date)
        result = await event_bus.send(query)
        
        # Use mapper to convert to response
        return MealMapper.to_daily_nutrition_response(result)
        
    except Exception as e:
        raise handle_exception(e)


@router.put("/{meal_id}/recalculate")
async def recalculate_meal_nutrition(
    meal_id: str,
    weight_grams: float = Query(..., description="New weight in grams", gt=0),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Recalculate meal nutrition based on new weight.
    
    This adjusts all nutritional values proportionally based on the weight change.
    """
    try:
        # Send command
        command = RecalculateMealNutritionCommand(
            meal_id=meal_id,
            weight_grams=weight_grams
        )
        
        result = await event_bus.send(command)
        
        # Return the updated nutrition result
        return {
            "success": True,
            "meal_id": result["meal_id"],
            "updated_nutrition": result["updated_nutrition"],
            "weight_grams": result["weight_grams"]
        }
        
    except Exception as e:
        raise handle_exception(e)