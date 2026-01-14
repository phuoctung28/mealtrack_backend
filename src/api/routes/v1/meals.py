"""
Meals API endpoints using event-driven architecture.
Clean separation with event bus pattern.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception, ValidationException
from src.api.mappers.meal_mapper import MealMapper
from src.api.schemas.request.meal_requests import (
    EditMealIngredientsRequest,
    CreateManualMealFromFoodsRequest
)
from src.api.schemas.response import (
    DetailedMealResponse,
    ManualMealCreationResponse
)
from src.api.schemas.response.daily_nutrition_response import DailyNutritionResponse
from src.app.commands.meal import (
    EditMealCommand,
    FoodItemChange,
    CustomNutritionData
)
from src.app.commands.meal.create_manual_meal_command import (
    CreateManualMealCommand,
    ManualMealItem,
)
from src.app.commands.meal.delete_meal_command import DeleteMealCommand
from src.app.commands.meal.upload_meal_image_immediately_command import UploadMealImageImmediatelyCommand
from src.app.queries.meal import (
    GetMealByIdQuery,
    GetDailyMacrosQuery
)
from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
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
    "FAILED": "failed",
    "INACTIVE": "inactive",
}



@router.post("/image/analyze", status_code=status.HTTP_200_OK, response_model=DetailedMealResponse)
async def analyze_meal_image_immediate(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    target_date: Optional[str] = Query(None, description="Target date in YYYY-MM-DD format for meal association"),
    language: str = Query("en", description="ISO 639-1 language code for response (en, vi, es, fr, de, ja, zh)"),
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
    
    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        # Validate content type
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationException(
                message=f"Invalid file type. Only {', '.join(ALLOWED_CONTENT_TYPES)} are allowed.",
                error_code="INVALID_FILE_TYPE",
                details={"content_type": file.content_type, "allowed": ALLOWED_CONTENT_TYPES}
            )
        
        # Read file content
        contents = await file.read()
        
        # Validate file size
        if len(contents) > MAX_FILE_SIZE:
            raise ValidationException(
                message=f"File size exceeds maximum allowed ({MAX_FILE_SIZE // (1024*1024)} MB)",
                error_code="FILE_SIZE_EXCEEDS_MAXIMUM",
                details={"size": len(contents), "max_size": MAX_FILE_SIZE}
            )
        
        # Parse target date if provided
        parsed_target_date = None
        if target_date:
            try:
                parsed_target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                logger.info("Target date specified: %s", parsed_target_date)
            except ValueError as e:
                raise ValidationException(
                    message="Invalid date format. Use YYYY-MM-DD format.",
                    error_code="INVALID_DATE_FORMAT",
                    details={"date": target_date}
                ) from e

        # Validate language code - default to 'en' if invalid
        valid_languages = ["en", "vi", "es", "fr", "de", "ja", "zh"]
        validated_language = language if language in valid_languages else "en"

        # Process the upload and analysis immediately
        logger.info("Processing meal photo for immediate analysis (target_date: %s, language: %s)", parsed_target_date, validated_language)

        command = UploadMealImageImmediatelyCommand(
            user_id=user_id,
            file_contents=contents,
            content_type=file.content_type,
            target_date=parsed_target_date,
            language=validated_language
        )
        
        logger.info("Uploading and analyzing meal immediately")
        meal = await event_bus.send(command)
        
        logger.info("Immediate analysis completed for meal ID: %s, status: %s", meal.meal_id, meal.status)
        
        # Check if analysis was successful
        if meal.status.value == "FAILED":
            error_message = meal.error_message or "Analysis failed"
            logger.error("Immediate analysis failed: %s", error_message)
            raise ValidationException(
                message=f"Failed to analyze meal image: {error_message}",
                error_code="FAILED_TO_ANALYZE_MEAL_IMAGE",
                details={"error_message": error_message}
            )
        
        # Get the image URL if available
        image_url = None
        if meal.image:
            # Try to get URL from image store
            image_store = CloudinaryImageStore()
            image_url = image_store.get_url(meal.image.image_id)
        
        # Return the detailed meal response using mapper
        return MealMapper.to_detailed_response(meal, image_url)

    except Exception as e:
        raise handle_exception(e) from e


@router.post("/manual", response_model=ManualMealCreationResponse)
async def create_manual_meal(
    payload: CreateManualMealFromFoodsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
) -> ManualMealCreationResponse:
    """
    Create a manual meal from USDA FDC items.

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        items = [
            ManualMealItem(fdc_id=i.fdc_id, quantity=i.quantity, unit=i.unit)
            for i in payload.items
        ]

        # Parse target_date if provided
        target_date = None
        if payload.target_date:
            try:
                target_date = datetime.strptime(payload.target_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationException(
                    message="Invalid date format. Use YYYY-MM-DD",
                    error_code="INVALID_DATE_FORMAT",
                    details={"date": payload.target_date}
                ) from e

        cmd = CreateManualMealCommand(
            user_id=user_id,
            items=items,
            dish_name=payload.dish_name,
            meal_type=payload.meal_type,
            target_date=target_date,
        )
        meal = await event_bus.send(cmd)

        return ManualMealCreationResponse(
            meal_id=meal.meal_id,
            status="success",
            message=f"Meal '{payload.dish_name}' created successfully",
            created_at=meal.created_at,
        )
    except Exception as e:
        raise handle_exception(e) from e


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
            image_store = CloudinaryImageStore()
            image_url = image_store.get_url(meal.image.image_id)
        
        # Use mapper to convert to response
        return MealMapper.to_detailed_response(meal, image_url)
        
    except Exception as e:
        raise handle_exception(e) from e
@router.delete("/{meal_id}")
async def delete_meal(
    meal_id: str,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """Mark a meal as INACTIVE (soft delete)."""
    try:
        command = DeleteMealCommand(meal_id=meal_id)
        result = await event_bus.send(command)
        return result
    except Exception as e:
        raise handle_exception(e) from e



@router.get("/daily/macros", response_model=DailyNutritionResponse)
async def get_daily_macros(
    user_id: str = Depends(get_current_user_id),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get daily macronutrient summary for all meals with user targets from TDEE.
    
    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        # Parse date
        target_date = None
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Send query with user_id for TDEE targets
        query = GetDailyMacrosQuery(user_id=user_id, target_date=target_date)
        result = await event_bus.send(query)
        
        # Use mapper to convert to response
        return MealMapper.to_daily_nutrition_response(result)
        
    except Exception as e:
        raise handle_exception(e) from e


@router.put("/{meal_id}/ingredients", response_model=None)
async def update_meal_ingredients(
    meal_id: str,
    request: EditMealIngredientsRequest,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Update meal ingredients and portions.
    
    Supports adding, removing, and modifying ingredients with automatic nutrition recalculation.
    """
    try:

        logger.info("Updating meal ingredients for meal %s", meal_id)
        # Convert request to command
        food_item_changes = []
        for change_request in request.food_item_changes:
            custom_nutrition = None
            if change_request.custom_nutrition:
                custom_nutrition = CustomNutritionData(
                    calories_per_100g=change_request.custom_nutrition.calories_per_100g,
                    protein_per_100g=change_request.custom_nutrition.protein_per_100g,
                    carbs_per_100g=change_request.custom_nutrition.carbs_per_100g,
                    fat_per_100g=change_request.custom_nutrition.fat_per_100g,
                )
            
            food_item_changes.append(
                FoodItemChange(
                    action=change_request.action,
                    id=change_request.id,
                    fdc_id=change_request.fdc_id,
                    name=change_request.name,
                    quantity=change_request.quantity,
                    unit=change_request.unit,
                    custom_nutrition=custom_nutrition
                )
            )

        logger.info("Food item changes: %s", food_item_changes)
        
        command = EditMealCommand(
            meal_id=meal_id,
            dish_name=request.dish_name,
            food_item_changes=food_item_changes
        )
        
        logger.info("Sending command to event bus: %s", command)
        result = await event_bus.send(command)
        return result
        
    except Exception as e:
        raise handle_exception(e) from e