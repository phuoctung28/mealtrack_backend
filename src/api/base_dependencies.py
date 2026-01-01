import logging
import os
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.food_cache_service_port import FoodCacheServicePort
from src.domain.ports.food_data_service_port import FoodDataServicePort
from src.domain.ports.ai_chat_service_port import AIChatServicePort
from src.domain.ports.food_mapping_service_port import FoodMappingServicePort
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.food_mapping_service import FoodMappingService
from src.domain.services.notification_service import NotificationService
from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
from src.infra.adapters.food_cache_service import FoodCacheService
from src.infra.adapters.food_data_service import FoodDataService
from src.infra.adapters.image_store import ImageStore
from src.infra.adapters.vision_ai_service import VisionAIService
from src.infra.cache.cache_service import CacheService
from src.infra.cache.metrics import CacheMonitor
from src.infra.cache.redis_client import RedisClient
from src.infra.database.config import SessionLocal
from src.infra.repositories.meal_repository import MealRepository
from src.infra.repositories.notification_repository import NotificationRepository
from src.infra.services.ai.openai_chat_service import OpenAIChatService
from src.infra.services.firebase_service import FirebaseService
from src.infra.services.scheduled_notification_service import ScheduledNotificationService
from src.infra.config.settings import settings


# Note: Old handler imports removed - using event-driven architecture now
# from src.app.handlers.activity_handler import ActivityHandler
# ... etc


# Globals
logger = logging.getLogger(__name__)
_redis_client: Optional[RedisClient] = None
_cache_service: Optional[CacheService] = None
_cache_monitor = CacheMonitor()

# Singleton service instances (initialized once, reused across requests)
_image_store: Optional[ImageStorePort] = None
_ai_chat_service: Optional[AIChatServicePort] = None
_vision_service: Optional[VisionAIServicePort] = None


async def initialize_cache_layer() -> None:
    """Initialize Redis cache if enabled."""
    global _redis_client, _cache_service

    if not settings.CACHE_ENABLED:
        logger.info("Caching disabled via settings")
        return

    if _redis_client is None:
        _redis_client = RedisClient(
            redis_url=settings.redis_url,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )
        await _redis_client.connect()

    _cache_service = CacheService(
        redis_client=_redis_client,
        default_ttl=settings.CACHE_DEFAULT_TTL,
        monitor=_cache_monitor,
        enabled=settings.CACHE_ENABLED,
    )


async def shutdown_cache_layer() -> None:
    """Gracefully close Redis connections."""
    global _redis_client, _cache_service

    if _cache_service:
        _cache_service = None
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None


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


# Image Store (singleton pattern)
def get_image_store() -> ImageStorePort:
    """
    Get the image store adapter instance (singleton).

    Returns:
        ImageStorePort: The image store adapter (Cloudinary or Mock)
    """
    global _image_store
    if _image_store is None:
        use_mock = bool(int(os.getenv("USE_MOCK_STORAGE", "0")))
        if use_mock:
            _image_store = ImageStore()
        else:
            _image_store = CloudinaryImageStore()
    return _image_store


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


# Vision Service (singleton pattern)
def get_vision_service() -> VisionAIServicePort:
    """
    Get the vision AI service instance (singleton).

    Returns:
        VisionAIServicePort: The vision service
    """
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionAIService()
    return _vision_service


# AI Chat Service (singleton pattern)
def get_ai_chat_service() -> AIChatServicePort:
    """
    Get the AI chat service instance (singleton) using the LLM provider factory.

    Supports multiple LLM providers (OpenAI, Gemini) with auto-detection.
    Provider selection priority:
    1. LLM_PROVIDER environment variable (if set)
    2. Auto-detect from available API keys (OPENAI_API_KEY > GOOGLE_API_KEY)

    Returns:
        AIChatServicePort: The configured LLM provider instance

    Raises:
        ValueError: If no LLM provider can be configured (no API keys available)
    """
    global _ai_chat_service
    if _ai_chat_service is not None:
        return _ai_chat_service

    from src.infra.services.ai.llm_provider_factory import LLMProviderFactory
    from src.infra.config.settings import settings

    try:
        provider = settings.LLM_PROVIDER
        if provider:
            logger.info(f"Using configured LLM provider: {provider}")

        # Get model from settings if available
        model = None
        if provider == "openai":
            model = settings.OPENAI_MODEL
        elif provider == "gemini":
            model = settings.GEMINI_MODEL

        _ai_chat_service = LLMProviderFactory.create_provider(
            provider=provider,
            model=model
        )
        return _ai_chat_service
    except ValueError as e:
        logger.error(f"Failed to create LLM provider: {e}")
        raise ValueError(
            "AI chat service is not available. "
            "Please configure at least one LLM provider by setting "
            "OPENAI_API_KEY or GOOGLE_API_KEY environment variable."
        ) from e


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
    return FoodCacheService(cache_service=_cache_service)


def get_cache_service() -> Optional[CacheService]:
    """Expose cache service for dependency injection."""
    return _cache_service


def get_cache_monitor() -> CacheMonitor:
    """Return shared cache monitor for metrics."""
    return _cache_monitor

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