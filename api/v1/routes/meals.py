import logging
from typing import Dict, List

from fastapi import APIRouter, UploadFile, HTTPException, status, Depends, File, Query

from api.dependencies import get_upload_meal_image_handler, get_meal_handler
from api.schemas.meal_schemas import (
    UpdateMealMacrosRequest, CreateMealRequest, UpdateMealRequest,
    MealResponse, DetailedMealResponse, PaginatedMealResponse,
    MealSearchRequest, MealSearchResponse, MealStatusResponse
)
from app.handlers.upload_meal_image_handler import UploadMealImageHandler
from app.handlers.meal_handler import MealHandler

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
    handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler),
):
    """Upload meal photo and return meal analysis with nutritional data."""
    try:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Only {', '.join(ALLOWED_CONTENT_TYPES)} are allowed."
            )
        
        contents = await file.read()
        
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed (8MB)"
            )
        
        # Reset file for handler
        await file.seek(0)
        
        logger.info("Analyzing meal photo")
        result = await handler.handle_meal_upload(file)
        logger.info(f"Meal created with ID: {result['meal_id']}")
        
        return result

    except HTTPException:
        raise
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
    """Retrieve meal information by its ID."""
    try:
        meal = meal_handler.get_meal(meal_id)
        if not meal:
            raise HTTPException(status_code=404, detail=f"Meal with ID {meal_id} not found")
        
        return DetailedMealResponse.from_domain(meal)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving meal: {str(e)}"
        )

@router.put("/{meal_id}", response_model=MealResponse)
async def update_meal(
    meal_id: str,
    meal_data: UpdateMealRequest,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """Update meal information and macros."""
    try:
        logger.info(f"Updating meal: {meal_id}")
        
        # For now, return a placeholder response
        # TODO: Implement actual meal update logic
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
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """Get paginated list of meals."""
    try:
        logger.info(f"Fetching meals - page: {page}, page_size: {page_size}")
        
        # For now, return sample meals
        # TODO: Implement actual pagination logic
        sample_meals = []
        for i in range(min(page_size, 5)):
            sample_meals.append(MealResponse(
                meal_id=f"meal-{i+1}",
                name=f"Sample Meal {i+1}",
                description=f"Description for meal {i+1}",
                status="ready",
                created_at="2024-01-01T00:00:00Z"
            ))
        
        return PaginatedMealResponse(
            meals=sample_meals,
            total=50,
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

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MealResponse)
async def create_meal(
    meal_data: CreateMealRequest,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """Create a new meal manually."""
    try:
        logger.info(f"Creating meal: {meal_data.name}")
        
        # For now, return a placeholder response
        # TODO: Implement actual meal creation logic
        meal_id = f"meal-{hash(meal_data.name) % 10000}"
        
        return MealResponse(
            meal_id=meal_id,
            name=meal_data.name,
            description=meal_data.description,
            serving_size=meal_data.serving_size,
            serving_unit=meal_data.serving_unit,
            calories_per_serving=meal_data.calories_per_serving,
            macros_per_serving=meal_data.macros_per_serving,
            status="created",
            created_at="2024-01-01T00:00:00Z"
        )
        
    except Exception as e:
        logger.error(f"Error creating meal: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating meal: {str(e)}"
        )

@router.delete("/{meal_id}")
async def delete_meal(
    meal_id: str,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """Delete a meal."""
    try:
        logger.info(f"Deleting meal: {meal_id}")
        
        # For now, return success
        # TODO: Implement actual meal deletion logic
        return {"message": f"Meal {meal_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting meal {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting meal: {str(e)}"
        )

@router.post("/{meal_id}/macros", response_model=Dict)
async def update_meal_macros(
    meal_id: str,
    macros_request: UpdateMealMacrosRequest,
    handler: UploadMealImageHandler = Depends(get_upload_meal_image_handler)
):
    """Update meal macros based on portion size with LLM recalculation."""
    try:
        new_amount = macros_request.size or macros_request.amount
        if not new_amount:
            raise HTTPException(status_code=400, detail="Either size or amount must be provided")
        
        unit = macros_request.unit or "g"
        
        logger.info(f"Updating macros for meal {meal_id} with portion: {new_amount} {unit}")
        
        result = await handler.update_meal_macros(meal_id, new_amount, unit)
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating meal macros for {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating meal macros: {str(e)}"
        )

@router.get("/{meal_id}/status", response_model=MealStatusResponse)
async def get_meal_status(
    meal_id: str,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """Get the current status of a meal analysis."""
    try:
        # For now, return a placeholder status
        # TODO: Implement actual status checking
        return MealStatusResponse(
            meal_id=meal_id,
            status="ready",
            status_message="Meal analysis complete",
            error_message=None
        )
        
    except Exception as e:
        logger.error(f"Error getting meal status for {meal_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting meal status: {str(e)}"
        )

@router.post("/search", response_model=MealSearchResponse)
async def search_meals(
    search_request: MealSearchRequest,
    meal_handler: MealHandler = Depends(get_meal_handler)
):
    """Search meals by name, description, or ingredients."""
    try:
        logger.info(f"Searching meals with query: '{search_request.query}'")
        
        # For now, return sample search results
        # TODO: Implement actual search logic
        sample_results = []
        if search_request.query:
            for i in range(min(search_request.limit, 3)):
                sample_results.append(MealResponse(
                    meal_id=f"search-result-{i+1}",
                    name=f"Meal matching '{search_request.query}' #{i+1}",
                    description=f"A delicious meal that matches your search for '{search_request.query}'",
                    status="ready",
                    created_at="2024-01-01T00:00:00Z"
                ))
        
        return MealSearchResponse(
            results=sample_results,
            query=search_request.query,
            total_results=len(sample_results)
        )
        
    except Exception as e:
        logger.error(f"Error searching meals: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching meals: {str(e)}"
        )

 