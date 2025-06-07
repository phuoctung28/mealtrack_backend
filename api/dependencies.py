"""
API dependencies for FastAPI dependency injection.

This module contains functions that provide dependencies to FastAPI endpoints.
"""

import os
from fastapi import Depends
from sqlalchemy.orm import Session

from app.handlers.meal_handler import MealHandler
from app.handlers.upload_meal_image_handler import UploadMealImageHandler
from domain.ports.meal_repository_port import MealRepositoryPort
from domain.ports.image_store_port import ImageStorePort
from domain.ports.vision_ai_service_port import VisionAIServicePort
from domain.services.gpt_response_parser import GPTResponseParser
from infra.repositories.meal_repository import MealRepository
from infra.adapters.image_store import ImageStore
from infra.adapters.cloudinary_image_store import CloudinaryImageStore
from infra.adapters.vision_ai_service import VisionAIService
from infra.database.config import get_db

# Check if we should use mock storage or Cloudinary
USE_MOCK_STORAGE = bool(int(os.getenv("USE_MOCK_STORAGE", "1")))

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
    if USE_MOCK_STORAGE:
        return ImageStore()
    else:
        return CloudinaryImageStore()

def get_vision_service() -> VisionAIServicePort:
    """
    Get the vision AI service instance.
    
    Returns:
        VisionAIServicePort: The vision AI service
    """
    return VisionAIService()

def get_gpt_parser() -> GPTResponseParser:
    """
    Get the GPT response parser instance.
    
    Returns:
        GPTResponseParser: The GPT response parser
    """
    return GPTResponseParser()

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