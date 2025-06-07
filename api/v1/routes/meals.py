import logging
from typing import Dict

from fastapi import APIRouter, UploadFile, HTTPException, status, Depends, File

from api.dependencies import get_upload_meal_image_handler
from api.schemas.meal_schemas import UpdateMealMacrosRequest
from app.handlers.upload_meal_image_handler import UploadMealImageHandler

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

 