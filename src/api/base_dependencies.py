import logging
import os
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from src.domain.services.meal_analysis.translation_service import MealAnalysisTranslationService
from src.domain.parsers.gpt_response_parser import GPTResponseParser
from src.domain.ports.food_cache_service_port import FoodCacheServicePort
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
from src.infra.adapters.open_food_facts_service import OpenFoodFactsService, get_open_food_facts_service
from src.infra.adapters.vision_ai_service import VisionAIService
from src.infra.cache.cache_service import CacheService
from src.infra.cache.metrics import CacheMonitor
from src.infra.cache.redis_client import RedisClient
from src.infra.config.settings import settings
from src.infra.database.config import get_db as get_db_from_config
from src.infra.repositories.meal_repository import MealRepository
from src.infra.repositories.notification_repository import NotificationRepository
from src.infra.services.firebase_service import FirebaseService
from src.infra.services.scheduled_notification_service import ScheduledNotificationService

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
    
    Uses scoped session from config for request isolation.
    This allows singleton services to safely access the current request's session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    # Delegate to the config's get_db which handles scoped sessions
    yield from get_db_from_config()


# Image Store (singleton pattern)
def get_image_store() -> ImageStorePort:
    """
    Get the image store adapter instance (singleton).

    Returns:
        ImageStorePort: The image store adapter (Cloudinary or Mock)
    """
    global _image_store
    if _image_store is None:
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


# GPT Parser
def get_gpt_parser() -> GPTResponseParser:
    """
    Get the GPT response parser instance.
    
    Returns:
        GPTResponseParser: The parser instance
    """
    return GPTResponseParser()


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


# Food Data Service (USDA FoodData Central)
def get_food_data_service() -> FoodDataService:
    """
    Get the food data service instance for USDA FoodData Central API.

    Returns:
        FoodDataService: The food data service
    """
    return FoodDataService()


# OpenFoodFacts Service
def get_open_food_facts_service_instance():
    """Get the OpenFoodFacts service instance."""
    return get_open_food_facts_service()


# FatSecret Service
def get_fat_secret_service_instance():
    """Get the FatSecret service instance."""
    from src.infra.adapters.fat_secret_service import get_fat_secret_service
    return get_fat_secret_service()


# Nutritionix Service
def get_nutritionix_service_instance():
    """Get the Nutritionix service instance, or None if not configured."""
    from src.infra.adapters.nutritionix_service import get_nutritionix_service
    return get_nutritionix_service()


# BraveSearch Nutrition Service (singleton — None when API key not configured)
_brave_search_nutrition_service = None


def get_brave_search_nutrition_service_instance():
    """Get the BraveSearch nutrition service singleton, or None if unconfigured."""
    global _brave_search_nutrition_service
    if _brave_search_nutrition_service is None:
        from src.infra.adapters.brave_search_nutrition_service import get_brave_search_nutrition_service
        from src.infra.adapters.meal_generation_service import MealGenerationService
        from src.domain.services.meal_suggestion.macro_validation_service import MacroValidationService

        meal_gen = MealGenerationService()
        macro_validator = MacroValidationService()
        _brave_search_nutrition_service = get_brave_search_nutrition_service(
            meal_generation_service=meal_gen,
            macro_validation_service=macro_validator,
        )
    return _brave_search_nutrition_service


# Food Reference Repository (replaces barcode_product_repository)
_food_reference_repository = None


def get_food_reference_repository():
    """Get the food reference repository singleton."""
    global _food_reference_repository
    if _food_reference_repository is None:
        from src.infra.repositories.food_reference_repository import FoodReferenceRepository
        _food_reference_repository = FoodReferenceRepository()
    return _food_reference_repository


# Backward-compatible alias
get_barcode_product_repository = get_food_reference_repository


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
        # Let NotificationRepository manage its own sessions to avoid ScopedSession here
        notification_repository = NotificationRepository()
        firebase_service = get_firebase_service()
        notification_service = NotificationService(notification_repository, firebase_service)
        _scheduled_notification_service = ScheduledNotificationService(
            notification_repository, 
            notification_service
        )
    return _scheduled_notification_service


# Phase 06: Meal Suggestion Dependencies
def get_redis_client() -> Optional[RedisClient]:
    """Get Redis client for meal suggestions repository."""
    return _redis_client


def get_meal_suggestion_repository():
    """Get meal suggestion repository (Phase 06)."""
    from src.infra.repositories.meal_suggestion_repository import MealSuggestionRepository
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Ensure cache layer is initialized.")
    return MealSuggestionRepository(_redis_client)


def get_suggestion_orchestration_service():
    """
    Get suggestion orchestration service (singleton-safe).
    
    This service uses ScopedSession internally to access the current request's
    database session, making it safe to use as a singleton in the event bus.
    """
    from src.domain.services.meal_suggestion.suggestion_orchestration_service import SuggestionOrchestrationService
    from src.infra.adapters.meal_generation_service import MealGenerationService
    from src.infra.database.config import SessionLocal
    from src.infra.repositories.user_repository import UserRepository

    meal_gen_service = MealGenerationService()
    suggestion_repo = get_meal_suggestion_repository()

    # Profile provider keeps domain decoupled from infra while still using SessionLocal
    def profile_provider(user_id: str):
        db = SessionLocal()
        try:
            repo = UserRepository(db)
            return repo.get_profile(user_id)
        finally:
            db.close()

    from src.infra.database.uow import UnitOfWork

    return SuggestionOrchestrationService(
        generation_service=meal_gen_service,
        suggestion_repo=suggestion_repo,
        profile_provider=profile_provider,
        uow_factory=UnitOfWork,
    )


# Note: Old handler functions removed - using event-driven architecture now
# The event bus configuration in event_bus.py handles all dependencies


# Meal Analysis Translation Service
def get_meal_translation_service() -> MealAnalysisTranslationService:
    """
    Get the meal analysis translation service instance.
    Repository uses session factory internally — safe for singletons.
    """
    from src.domain.services.meal_suggestion.translation_service import TranslationService
    from src.domain.services.meal_analysis.translation_service import MealAnalysisTranslationService
    from src.infra.repositories.meal_translation_repository import MealTranslationRepository
    from src.infra.adapters.meal_generation_service import MealGenerationService

    translation_repo = MealTranslationRepository()  # uses SessionLocal factory
    generation_service = MealGenerationService()
    translation_service = TranslationService(generation_service)

    return MealAnalysisTranslationService(
        translation_repo=translation_repo,
        translation_service=translation_service
    )


def get_translation_service() -> "TranslationService":
    """Get lightweight TranslationService for translating strings via Gemini."""
    from src.domain.services.meal_suggestion.translation_service import TranslationService
    from src.infra.adapters.meal_generation_service import MealGenerationService

    return TranslationService(MealGenerationService())


# Singleton subscription service instance
_subscription_service: Optional["SubscriptionServicePort"] = None


def get_subscription_service() -> "SubscriptionServicePort":
    """
    Get the subscription service instance.

    Returns:
        SubscriptionServicePort: The subscription service
    """
    global _subscription_service

    if _subscription_service is None:
        from src.infra.adapters.revenuecat_adapter import RevenueCatAdapter
        api_key = os.getenv("REVENUECAT_SECRET_API_KEY", "")
        _subscription_service = RevenueCatAdapter(api_key=api_key)

    return _subscription_service