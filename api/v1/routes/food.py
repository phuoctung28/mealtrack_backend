from fastapi import APIRouter, UploadFile, HTTPException, status, Depends, File, BackgroundTasks
from typing import Dict, List
from api.schemas.food_schemas import (
    CreateFoodRequest, UpdateFoodRequest, UpdateFoodMacrosRequest,
    FoodResponse, FoodPhotoResponse, PaginatedFoodResponse,
    FoodSearchRequest, FoodSearchResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/food",
    tags=["food"],
)

# Maximum file size (8 MB)
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB in bytes

# Allowed content types
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png"]

@router.post("/photo", status_code=status.HTTP_201_CREATED, response_model=FoodPhotoResponse)
async def analyze_food_photo(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    # handler: FoodPhotoHandler = Depends(get_food_photo_handler),
):
    """
    Send food photo and return food name with its macros.
    
    - Accepts image/jpeg or image/png files up to 8MB
    - Returns food identification and nutritional analysis
    - Must priority endpoint
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
        
        # TODO: Implement food photo analysis
        # This should use the vision AI service to identify food and calculate macros
        logger.info("Analyzing food photo")
        
        # Placeholder response - implement actual analysis
        return FoodPhotoResponse(
            food_name="Placeholder Food",
            confidence=0.85,
            macros={
                "protein": 25.0,
                "carbs": 30.0,
                "fat": 10.0,
                "fiber": 5.0
            },
            calories=290.0,
            analysis_id="temp-analysis-id"
        )
        
    except Exception as e:
        logger.error(f"Error analyzing food photo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing food photo: {str(e)}"
        )

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=FoodResponse)
async def create_food(
    food_data: CreateFoodRequest,
    # handler: FoodHandler = Depends(get_food_handler),
):
    """
    Add food info and macros.
    
    - Creates a new food item in the database
    - Should priority endpoint
    """
    try:
        # TODO: Implement food creation
        logger.info(f"Creating food: {food_data.name}")
        
        # Placeholder response - implement actual creation
        return FoodResponse(
            food_id="temp-food-id",
            name=food_data.name,
            brand=food_data.brand,
            description=food_data.description,
            serving_size=food_data.serving_size,
            serving_unit=food_data.serving_unit,
            calories_per_serving=food_data.calories_per_serving,
            macros_per_serving=food_data.macros_per_serving,
            micros_per_serving=food_data.micros_per_serving,
            barcode=food_data.barcode,
            image_url=food_data.image_url,
            is_verified=False,
            created_at="2024-01-01T00:00:00Z"
        )
        
    except Exception as e:
        logger.error(f"Error creating food: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating food: {str(e)}"
        )

@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(
    food_id: str,
    # handler: FoodHandler = Depends(get_food_handler)
):
    """
    Retrieve information by its id.
    
    - Returns complete food information including nutritional data
    - Must priority endpoint
    """
    try:
        # TODO: Implement food retrieval
        logger.info(f"Retrieving food: {food_id}")
        
        # Placeholder response - implement actual retrieval
        return FoodResponse(
            food_id=food_id,
            name="Sample Food",
            brand="Sample Brand",
            description="Sample food description",
            serving_size=100.0,
            serving_unit="g",
            calories_per_serving=250.0,
            macros_per_serving={
                "protein": 20.0,
                "carbs": 25.0,
                "fat": 8.0,
                "fiber": 3.0
            },
            is_verified=True,
            created_at="2024-01-01T00:00:00Z"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving food {food_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving food: {str(e)}"
        )

@router.put("/{food_id}", response_model=FoodResponse)
async def update_food(
    food_id: str,
    food_data: UpdateFoodRequest,
    # handler: FoodHandler = Depends(get_food_handler)
):
    """
    Update food info and macros.
    
    - Updates existing food item
    - Must priority endpoint
    """
    try:
        # TODO: Implement food update
        logger.info(f"Updating food: {food_id}")
        
        # Placeholder response - implement actual update
        return FoodResponse(
            food_id=food_id,
            name=food_data.name or "Updated Food",
            brand=food_data.brand,
            description=food_data.description,
            serving_size=food_data.serving_size,
            serving_unit=food_data.serving_unit,
            calories_per_serving=food_data.calories_per_serving,
            macros_per_serving=food_data.macros_per_serving,
            micros_per_serving=food_data.micros_per_serving,
            barcode=food_data.barcode,
            image_url=food_data.image_url,
            is_verified=False,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T12:00:00Z"
        )
        
    except Exception as e:
        logger.error(f"Error updating food {food_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating food: {str(e)}"
        )

@router.post("/{food_id}/macros", response_model=Dict)
async def update_food_macros(
    food_id: str,
    macros_data: UpdateFoodMacrosRequest,
    # handler: FoodHandler = Depends(get_food_handler)
):
    """
    Send size and/or amount of food to update food macros.
    
    - Calculates new macros based on portion size/amount
    - Must priority endpoint
    """
    try:
        # TODO: Implement macros calculation based on size/amount
        logger.info(f"Updating macros for food {food_id} with size/amount")
        
        # Placeholder response - implement actual calculation
        return {
            "food_id": food_id,
            "original_serving": {
                "size": 100.0,
                "unit": "g",
                "calories": 250.0,
                "macros": {
                    "protein": 20.0,
                    "carbs": 25.0,
                    "fat": 8.0,
                    "fiber": 3.0
                }
            },
            "adjusted_serving": {
                "size": macros_data.size or macros_data.amount,
                "unit": macros_data.unit or "g",
                "calories": 375.0,  # Calculated based on new size
                "macros": {
                    "protein": 30.0,
                    "carbs": 37.5,
                    "fat": 12.0,
                    "fiber": 4.5
                }
            },
            "scaling_factor": 1.5
        }
        
    except Exception as e:
        logger.error(f"Error updating food macros for {food_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating food macros: {str(e)}"
        ) 