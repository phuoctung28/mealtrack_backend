import os

from fastapi import Depends
from sqlalchemy.orm import Session

from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
from src.infra.adapters.image_store import ImageStore
from src.infra.adapters.vision_ai_service import VisionAIService
from src.infra.database.config import SessionLocal
from src.infra.repositories.meal_repository import MealRepository


# Note: Old handler imports removed - using event-driven architecture now
# from src.app.handlers.activity_handler import ActivityHandler
# ... etc


# Database
def get_db():
    """
    Get a database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Image Store
def get_image_store() -> ImageStorePort:
    """
    Get the image store adapter instance.
    
    Returns:
        ImageStorePort: The image store adapter (Cloudinary or Mock)
    """
    use_mock = os.getenv("USE_MOCK_STORAGE", "false").lower() == "true"
    
    if use_mock:
        return ImageStore()
    else:
        return CloudinaryImageStore()


# Meal Repository
def get_meal_repository(db: Session = Depends(get_db)) -> MealRepositoryPort:
    """
    Get the meal repository instance.
    
    Args:
        db: Database session
        
    Returns:
        MealRepositoryPort: The meal repository
    """
    return MealRepository(db)


# Vision Service
def get_vision_service() -> VisionAIServicePort:
    """
    Get the vision AI service instance.
    
    Returns:
        VisionAIServicePort: The vision service
    """
    
    return VisionAIService()


# GPT Parser
def get_gpt_parser() -> GPTResponseParser:
    """
    Get the GPT response parser instance.
    
    Returns:
        GPTResponseParser: The parser instance
    """
    return GPTResponseParser()


# Note: Old handler functions removed - using event-driven architecture now
# The event bus configuration in event_bus.py handles all dependencies