import os

from fastapi import Depends
from sqlalchemy.orm import Session

from src.app.handlers.meal_handler import MealHandler
from src.app.handlers.tdee_handler import TdeeHandler
from src.app.handlers.upload_meal_image_handler import UploadMealImageHandler
from src.app.services.meal_ingredient_service import MealIngredientService
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.tdee_service import TdeeCalculationService
from src.infra.adapters.image_store import ImageStore
from src.infra.adapters.mock_vision_ai_service import MockVisionAIService
from src.infra.database.config import get_db
from src.infra.repositories.meal_repository import MealRepository

try:
    from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False

try:
    from src.infra.adapters.vision_ai_service import VisionAIService
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
    if VISION_AI_AVAILABLE:
        try:
            return VisionAIService()
        except Exception:
            # Fall back to mock if real service fails to initialize
            return MockVisionAIService()
    else:
        return MockVisionAIService()

def get_gpt_parser() -> GPTResponseParser:
    """
    Get the GPT response parser instance.
    
    Returns:
        GPTResponseParser: The GPT response parser
    """
    return GPTResponseParser()

def get_meal_ingredient_service() -> MealIngredientService:
    """
    Get the meal ingredient service instance (singleton).
    
    Returns:
        MealIngredientService: The meal ingredient service
    """
    global _ingredient_service
    if _ingredient_service is None:
        _ingredient_service = MealIngredientService()
    return _ingredient_service

def get_meal_handler(
    meal_repository: MealRepositoryPort = Depends(get_meal_repository),
    image_store: ImageStorePort = Depends(get_image_store)
) -> MealHandler:
    """
    Get the meal handler instance.
    
    Returns:
        MealHandler: The meal handler
    """
    return MealHandler(
        meal_repository=meal_repository,
        image_store=image_store
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

def get_tdee_handler() -> TdeeHandler:
    """Dependency injection for TDEE handler."""
    tdee_service = TdeeCalculationService()
    return TdeeHandler(tdee_service) 