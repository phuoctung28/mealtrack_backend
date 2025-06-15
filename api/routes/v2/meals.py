import logging
from typing import Dict

from fastapi import APIRouter, UploadFile, HTTPException, status, Depends, File, BackgroundTasks

from api.dependencies import get_upload_meal_image_handler
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