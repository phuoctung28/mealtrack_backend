import logging

from fastapi import APIRouter, UploadFile, HTTPException, status, Depends, File, BackgroundTasks

from api.dependencies import get_upload_meal_image_handler, get_meal_handler, get_activities_handler
from api.mappers import MealMapper, ActivityMapper
from api.schemas import (
    UpdateMealMacrosRequest,
    MealResponse,
    MealStatusResponse,
    DetailedMealResponse,
    ActivitiesResponse
)
from app.handlers.activities_handler import ActivitiesHandler
from app.handlers.meal_handler import MealHandler
from app.handlers.upload_meal_image_handler import UploadMealImageHandler

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/meals",
    tags=["meals"],
)

MAX_FILE_SIZE = 8 * 1024 * 1024

ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png"]

@router.post("/image", status_code=status.HTTP_200_OK, response_model=DetailedMealResponse)
async def upload_meal_image(
    file: UploadFile = File(...),
    handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler),
    meal_handler: MealHandler = Depends(get_meal_handler),
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
        
        # Return the detailed meal response using mapper in API layer
        # Extract meal analysis (name + ingredients) using app layer service
        meal_analysis = meal_handler.extract_meal_analysis_from_meal(meal)
        
        # Get ingredients and meal name
        ingredient_data = meal_analysis.ingredients if meal_analysis else None
        extracted_meal_name = meal_analysis.meal_name if meal_analysis else None
        
        # Convert to DTOs using API layer mapper (pure conversion)
        ingredient_dtos = MealMapper.convert_ingredient_data_to_dtos(ingredient_data)
        
        # Create complete response with meal name and ingredient data
        return MealMapper.to_detailed_response(meal, ingredient_dtos, extracted_meal_name)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in immediate meal analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing meal photo: {str(e)}"
        )

@router.get("/activities", response_model=ActivitiesResponse)
async def get_user_activities(
    page: int = 1,
    page_size: int = 20,
    activities_handler: ActivitiesHandler = Depends(get_activities_handler)
):
    """
    Retrieve all user activities including food results after scanning or manually adding.
    
    This endpoint returns a paginated list of persisted meals with enriched data.
    Designed to be scalable - will include training and scan body data in future updates.
    
    - **Must priority endpoint for activity tracking**
    - Returns enriched meal data with nutritional information
    - Supports filtering by meal status
    - Paginated for optimal performance
    - Scalable design for future activity types
    - Follows mediator pattern with handler-based architecture
    
    Args:
        page: Page number (starts from 1)
        page_size: Number of items per page (1-100)
        activities_handler: Injected activities handler (mediator)
        
    Returns:
        Paginated list of user activities with enriched meal data
    """
    try:
        # Delegate business logic to the handler (mediator pattern)
        result = activities_handler.get_user_activities(
            page=page,
            page_size=page_size,
        )
        
        # Transform meals to enriched activity format using mapper
        activities = [ActivityMapper.meal_to_activity(meal) for meal in result["meals"]]
        
        # Use mapper to convert to proper DTO response
        response = ActivityMapper.to_activities_response(activities, result["pagination"], result["metadata"])
        
        logger.info(f"Retrieved {len(response.activities)} activities via handler "
                   f"(page {response.pagination.current_page}/{response.pagination.total_pages}, "
                   f"total: {response.pagination.total_items})")
        
        return response
        
    except ValueError as e:
        # Handler validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving user activities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving activities: {str(e)}"
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
    
    # Extract meal analysis (name + ingredients) using app layer service
    meal_analysis = meal_handler.extract_meal_analysis_from_meal(meal)
    
    # Get ingredients and meal name
    ingredient_data = meal_analysis.ingredients if meal_analysis else None
    extracted_meal_name = meal_analysis.meal_name if meal_analysis else None
    
    # Convert to DTOs using API layer mapper (pure conversion)
    ingredient_dtos = MealMapper.convert_ingredient_data_to_dtos(ingredient_data)
    
    # Create complete response with meal name and ingredient data
    return MealMapper.to_detailed_response(meal, ingredient_dtos, extracted_meal_name)

@router.post("/{meal_id}/macros", response_model=MealResponse)
async def update_meal_macros(
    meal_id: str,
    macros_request: UpdateMealMacrosRequest,
    background_tasks: BackgroundTasks,
    meal_handler: MealHandler = Depends(get_meal_handler),
    upload_handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler)
):
    """
    Update meal macros based on actual weight in grams.
    
    - Updates meal macros based on precise weight measurement
    - Triggers LLM-based nutrition recalculation for accuracy
    - Must priority endpoint for portion adjustment
    """
    try:
        logger.info(f"Updating macros for meal {meal_id} with weight: {macros_request.weight_grams}g")
        
        # Delegate all business logic to handler
        result = meal_handler.update_meal_macros_with_weight(
            meal_id, 
            macros_request.weight_grams, 
            background_tasks,
            upload_handler
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Meal with ID {meal_id} not found")
        
        logger.info(f"Successfully updated meal {meal_id} weight to {macros_request.weight_grams}g")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating macros for meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating meal macros: {str(e)}"
        )

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
    
    # Use API layer mapper to convert to DTO
    status_message = meal_handler.get_status_message(meal)
    return MealMapper.to_status_response(meal, status_message) 