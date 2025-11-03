import os

from fastapi import Depends
from sqlalchemy.orm import Session

from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.food_cache_service_port import FoodCacheServicePort
from src.domain.ports.food_data_service_port import FoodDataServicePort
from src.domain.ports.food_mapping_service_port import FoodMappingServicePort
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.food_mapping_service import FoodMappingService
from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
from src.infra.adapters.food_cache_service import FoodCacheService
from src.infra.adapters.food_data_service import FoodDataService
from src.infra.adapters.image_store import ImageStore
from src.infra.adapters.vision_ai_service import VisionAIService
from src.infra.database.config import SessionLocal
from src.infra.repositories.meal_repository import MealRepository
from src.infra.repositories.notification_repository import NotificationRepository
from src.infra.services.firebase_service import FirebaseService
from src.domain.services.notification_service import NotificationService
from src.infra.services.scheduled_notification_service import ScheduledNotificationService


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
    use_mock = bool(int(os.getenv("USE_MOCK_STORAGE", "0")))
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

# Food Data Service
def get_food_data_service() -> FoodDataServicePort:
    """
    Get the food data service instance.
    
    Returns:
        FoodDataServicePort: The food data service
    """
    return FoodDataService()

# Food Cache Service
def get_food_cache_service() -> FoodCacheServicePort:
    """
    Get the food cache service instance.
    
    Returns:
        FoodCacheServicePort: The food cache service
    """
    return FoodCacheService()

# Food Mapping Service
def get_food_mapping_service() -> FoodMappingServicePort:
    """
    Get the food mapping service instance.
    
    Returns:
        FoodMappingServicePort: The food mapping service
    """
    return FoodMappingService()

# Notification Repository
def get_notification_repository(db: Session = Depends(get_db)) -> NotificationRepositoryPort:
    """
    Get the notification repository instance.
    
    Args:
        db: Database session
        
    Returns:
        NotificationRepositoryPort: The notification repository
    """
    return NotificationRepository(db)


# Firebase Service (singleton pattern - create once and reuse)
_firebase_service = None

def get_firebase_service() -> FirebaseService:
    """
    Get the Firebase service instance (singleton).
    
    Returns:
        FirebaseService: The Firebase service
    """
    global _firebase_service
    if _firebase_service is None:
        _firebase_service = FirebaseService()
    return _firebase_service


# Notification Service
def get_notification_service(
    notification_repository: NotificationRepositoryPort = Depends(get_notification_repository),
    firebase_service: FirebaseService = Depends(get_firebase_service)
) -> NotificationService:
    """
    Get the notification service instance.
    
    Args:
        notification_repository: Notification repository
        firebase_service: Firebase service
        
    Returns:
        NotificationService: The notification service
    """
    return NotificationService(notification_repository, firebase_service)


# Scheduled Notification Service (singleton pattern - create once and reuse)
_scheduled_notification_service = None

def get_scheduled_notification_service() -> ScheduledNotificationService:
    """
    Get the scheduled notification service instance (singleton).
    This is created during application startup in the lifespan function.
    
    Returns:
        ScheduledNotificationService: The scheduled notification service
    """
    return _scheduled_notification_service


def initialize_scheduled_notification_service() -> ScheduledNotificationService:
    """
    Initialize the scheduled notification service during application startup.
    
    Returns:
        ScheduledNotificationService: The initialized scheduled notification service
    """
    global _scheduled_notification_service
    if _scheduled_notification_service is None:
        # Create instances without using Depends (we're not in request context)
        notification_repository = NotificationRepository()
        firebase_service = get_firebase_service()
        notification_service = NotificationService(notification_repository, firebase_service)
        _scheduled_notification_service = ScheduledNotificationService(
            notification_repository, 
            notification_service
        )
    return _scheduled_notification_service


# Note: Old handler functions removed - using event-driven architecture now
# The event bus configuration in event_bus.py handles all dependencies