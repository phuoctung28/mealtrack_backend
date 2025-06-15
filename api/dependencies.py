import os

from fastapi import Depends
from sqlalchemy.orm import Session

from app.handlers.activities_handler import ActivitiesHandler
from app.handlers.meal_handler import MealHandler
from app.handlers.upload_meal_image_handler import UploadMealImageHandler
from app.services.gpt_response_parser import GPTResponseParser
from app.services.ingredient_extraction_service import IngredientExtractionService
from domain.ports.image_store_port import ImageStorePort
from domain.ports.meal_repository_port import MealRepositoryPort
from domain.ports.vision_ai_service_port import VisionAIServicePort
from infra.adapters.image_store import ImageStore
from infra.database.config import get_db
from infra.repositories.meal_repository import MealRepository

try:
    from infra.adapters.cloudinary_image_store import CloudinaryImageStore
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False

try:
    from infra.adapters.vision_ai_service import VisionAIService
    VISION_AI_AVAILABLE = True
except ImportError:
    VISION_AI_AVAILABLE = False

USE_MOCK_STORAGE = bool(int(os.getenv("USE_MOCK_STORAGE", "1")))

_ingredient_service = None

def get_meal_repository(db: Session = Depends(get_db)) -> MealRepositoryPort:
    """
    Get the meal repository instance.
    
    Returns:
        MealRepositoryPort: The meal repository
    """
    return MealRepository(db=db)

def get_image_store() -> ImageStorePort:
    """
    Get the image store instance.
    
    Returns:
        ImageStorePort: The image store (either local or Cloudinary)
    """
    if USE_MOCK_STORAGE or not CLOUDINARY_AVAILABLE:
        return ImageStore()
    else:
        return CloudinaryImageStore()

def get_vision_service() -> VisionAIServicePort:
    """
    Get the vision AI service instance.
    
    Returns:
        VisionAIServicePort: The vision AI service (real or mock)
    """
    return VisionAIService()

def get_gpt_parser() -> GPTResponseParser:
    """
    Get the GPT response parser instance.
    
    Returns:
        GPTResponseParser: The GPT response parser
    """
    return GPTResponseParser()

def get_ingredient_extraction_service() -> IngredientExtractionService:
    """
    Get the ingredient extraction service instance.
    
    Returns:
        IngredientExtractionService: The ingredient extraction service
    """
    return IngredientExtractionService()

def get_meal_handler(
    meal_repository: MealRepositoryPort = Depends(get_meal_repository),
    image_store: ImageStorePort = Depends(get_image_store),
    ingredient_extraction_service: IngredientExtractionService = Depends(get_ingredient_extraction_service)
) -> MealHandler:
    """
    Get the meal handler instance.
    
    Returns:
        MealHandler: The meal handler
    """
    return MealHandler(
        meal_repository=meal_repository,
        image_store=image_store,
        ingredient_extraction_service=ingredient_extraction_service
    )

def get_upload_meal_image_handler(
    image_store: ImageStorePort = Depends(get_image_store),
    meal_repository: MealRepositoryPort = Depends(get_meal_repository),
    vision_service: VisionAIServicePort = Depends(get_vision_service),
    gpt_parser: GPTResponseParser = Depends(get_gpt_parser)
) -> UploadMealImageHandler:
    """
    Get the upload meal image handler instance.
    
    Returns:
        UploadMealImageHandler: The upload meal image handler
    """
    return UploadMealImageHandler(
        image_store=image_store,
        meal_repository=meal_repository,
        vision_service=vision_service,
        gpt_parser=gpt_parser
    )

def get_activities_handler(
    meal_repository: MealRepositoryPort = Depends(get_meal_repository)
) -> ActivitiesHandler:
    """
    Get the activities handler instance.
    
    Returns:
        ActivitiesHandler: The activities handler for managing user activities
    """
    return ActivitiesHandler(meal_repository=meal_repository) 