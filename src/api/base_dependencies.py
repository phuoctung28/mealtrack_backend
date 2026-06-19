import logging
import os
from typing import TYPE_CHECKING, Optional

from src.domain.parsers.vision_response_parser import VisionResponseParser
from src.domain.ports.food_cache_service_port import FoodCacheServicePort
from src.domain.ports.food_mapping_service_port import FoodMappingServicePort
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.food_mapping_service import FoodMappingService
from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
from src.infra.adapters.food_cache_service import FoodCacheService
from src.infra.adapters.food_data_service import FoodDataService
from src.infra.adapters.open_food_facts_service import (
    get_open_food_facts_service,
)
from src.infra.adapters.vision_ai_service import VisionAIService
from src.infra.cache.cache_service import CacheService
from src.infra.cache.metrics import CacheMonitor
from src.infra.cache.redis_client import RedisClient
from src.infra.config.settings import settings
from src.infra.database.config_async import get_async_db
from src.infra.services.firebase_service import FirebaseService

if TYPE_CHECKING:
    from src.domain.ports.subscription_service_port import SubscriptionServicePort

# Note: Old handler imports removed - using event-driven architecture now
# from src.app.handlers.activity_handler import ActivityHandler
# ... etc


# Globals
logger = logging.getLogger(__name__)
_redis_client: RedisClient | None = None
_cache_service: CacheService | None = None
_cache_monitor = CacheMonitor()

# Singleton service instances (initialized once, reused across requests)
_image_store: ImageStorePort | None = None
_vision_service: VisionAIServicePort | None = None


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
async def get_db():
    """Backward-compatible FastAPI dependency that yields an async DB session."""
    async for session in get_async_db():
        yield session


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


# Vision Response Parser
def get_vision_parser() -> VisionResponseParser:
    """
    Get the vision response parser instance.

    Returns:
        VisionResponseParser: The parser instance
    """
    return VisionResponseParser(strict_schema_mode=True)


# Backward-compat alias so existing code referring to get_gpt_parser continues to work.
get_gpt_parser = get_vision_parser


# Food Cache Service
def get_food_cache_service() -> FoodCacheServicePort:
    """
    Get the food cache service instance.

    Returns:
        FoodCacheServicePort: The food cache service
    """
    return FoodCacheService(cache_service=_cache_service)


def get_cache_service() -> CacheService | None:
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


# fatsecret Service
def get_fat_secret_service_instance():
    """Get the fatsecret service instance."""
    from src.infra.adapters.fat_secret_service import get_fat_secret_service

    return get_fat_secret_service()


# Food Reference Repository (replaces barcode_product_repository)
_async_food_reference_repository = None


def get_async_food_reference_repository():
    """Get the async food reference repository adapter singleton."""
    global _async_food_reference_repository
    if _async_food_reference_repository is None:
        from src.infra.repositories.food_reference_uow_adapter import (
            AsyncFoodReferenceUowAdapter,
        )

        _async_food_reference_repository = AsyncFoodReferenceUowAdapter()
    return _async_food_reference_repository


# Backward-compatible aliases for older callers; runtime receives async adapter.
get_food_reference_repository = get_async_food_reference_repository
get_barcode_product_repository = get_food_reference_repository


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


def get_daily_context_precompute_service():
    """Get daily context precompute service for notification rescheduling."""
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    return DailyContextPrecomputeService()


# Phase 06: Meal Suggestion Dependencies
def get_raw_redis_client():
    """Return the underlying async Redis client (None if not initialized)."""
    return _redis_client.client if _redis_client and _redis_client.client else None


def get_meal_suggestion_repository():
    """Get Redis-backed meal suggestion session store."""
    from src.infra.repositories.meal_suggestion_repository import (
        MealSuggestionRepository,
    )

    if _redis_client is None:
        raise RuntimeError(
            "Redis suggestion session store not initialized. "
            "Meal suggestion sessions require Redis until moved to durable storage."
        )
    return MealSuggestionRepository(_redis_client)


_deepl_suggestion_translation_service = None


def get_deepl_suggestion_translation_service():
    """Get DeepL-backed suggestion translation service (singleton).

    Returns None if DEEPL_API_KEY is not set (generation still works, just in English).
    """
    global _deepl_suggestion_translation_service

    if _deepl_suggestion_translation_service is not None:
        return _deepl_suggestion_translation_service

    # Requires text translation service
    text_service = get_deepl_text_translation_service()
    if text_service is None:
        logger.warning("DEEPL_API_KEY not set – suggestion translation will be skipped")
        return None

    from src.domain.services.meal_suggestion import (
        deepl_suggestion_translation_service,
    )

    service_cls = deepl_suggestion_translation_service.DeepLSuggestionTranslationService
    _deepl_suggestion_translation_service = service_cls(
        text_translation_service=text_service
    )
    logger.info("DeepL suggestion translation service initialised")
    return _deepl_suggestion_translation_service


def get_suggestion_orchestration_service():
    """
    Get suggestion orchestration service (singleton-safe).

    This service uses AsyncUnitOfWork for DB-backed user profile lookups.
    """
    from src.domain.services.meal_suggestion.suggestion_orchestration_service import (
        SuggestionOrchestrationService,
    )
    from src.infra.adapters.meal_generation_service import MealGenerationService
    from src.infra.database.uow_async import AsyncUnitOfWork
    from src.infra.services.ai.schemas import (
        DiscoveryMealsResponse,
        MealNamesResponse,
        RecipeDetailsResponse,
    )

    meal_gen_service = MealGenerationService()
    suggestion_repo = get_meal_suggestion_repository()

    async def profile_provider(user_id: str):
        async with AsyncUnitOfWork() as uow:
            return await uow.users.get_profile(user_id)

    return SuggestionOrchestrationService(
        generation_service=meal_gen_service,
        suggestion_repo=suggestion_repo,
        nutrition_lookup=get_nutrition_lookup_service(),
        profile_provider=profile_provider,
        uow_factory=AsyncUnitOfWork,
        meal_names_schema_class=MealNamesResponse,
        discovery_meals_schema_class=DiscoveryMealsResponse,
        recipe_details_schema_class=RecipeDetailsResponse,
        translation_service=get_deepl_suggestion_translation_service(),
    )


# Note: Old handler functions removed - using event-driven architecture now
# The event bus configuration in event_bus.py handles all dependencies


_deepl_meal_translation_service = None
_async_meal_translation_repository = None


def get_async_meal_translation_repository():
    """Get the async meal translation repository adapter singleton."""
    global _async_meal_translation_repository
    if _async_meal_translation_repository is None:
        from src.infra.repositories.meal_translation_uow_adapter import (
            AsyncMealTranslationUowAdapter,
        )

        _async_meal_translation_repository = AsyncMealTranslationUowAdapter()
    return _async_meal_translation_repository


def get_deepl_meal_translation_service():
    """Get DeepL-backed meal translation service (singleton).

    Returns None if DEEPL_API_KEY is not configured so callers can
    treat translation as optional.
    """
    global _deepl_meal_translation_service

    if _deepl_meal_translation_service is not None:
        return _deepl_meal_translation_service

    # Requires text translation service
    text_service = get_deepl_text_translation_service()
    if text_service is None:
        logger.warning("DEEPL_API_KEY not set – meal translation will be skipped")
        return None

    from src.domain.services.meal_analysis.deepl_meal_translation_service import (
        DeepLMealTranslationService,
    )

    _deepl_meal_translation_service = DeepLMealTranslationService(
        translation_repo=get_async_meal_translation_repository(),
        text_translation_service=text_service,
    )
    logger.info("DeepL meal translation service initialised")
    return _deepl_meal_translation_service


_deepl_text_translation_service = None


def get_deepl_text_translation_service():
    """Get DeepL-backed text translation service (singleton).

    Used for ingredient recognition, food search, barcode lookup, and meal text parsing.
    Returns None if DEEPL_API_KEY is not configured.
    """
    global _deepl_text_translation_service

    if _deepl_text_translation_service is not None:
        return _deepl_text_translation_service

    if not settings.DEEPL_API_KEY:
        logger.warning("DEEPL_API_KEY not set – text translation will be skipped")
        return None

    from src.domain.services.translation.deepl_text_translation_service import (
        DeepLTextTranslationService,
    )
    from src.infra.adapters.deepl_translation_adapter import DeepLTranslationAdapter

    _deepl_text_translation_service = DeepLTextTranslationService(
        deepl_port=DeepLTranslationAdapter(settings.DEEPL_API_KEY),
    )
    logger.info("DeepL text translation service initialised")
    return _deepl_text_translation_service


# IngredientNutritionResolver singleton reuses fatsecret and food references.
_ingredient_nutrition_resolver = None


def get_ingredient_nutrition_resolver():
    """Get IngredientNutritionResolver singleton."""
    global _ingredient_nutrition_resolver
    if _ingredient_nutrition_resolver is None:
        from src.domain.services.meal_suggestion.ingredient_nutrition_resolver import (
            IngredientNutritionResolver,
        )

        _ingredient_nutrition_resolver = IngredientNutritionResolver(
            fatsecret=get_fat_secret_service_instance(),
            food_ref_repo=get_async_food_reference_repository(),
        )
    return _ingredient_nutrition_resolver


# NutritionLookupService singleton uses food refs, resolver, and generation.
_nutrition_lookup_service = None


def get_nutrition_lookup_service():
    """Get NutritionLookupService singleton."""
    global _nutrition_lookup_service
    if _nutrition_lookup_service is None:
        from src.domain.services.meal_suggestion.nutrition_lookup_service import (
            NutritionLookupService,
        )
        from src.infra.adapters.meal_generation_service import MealGenerationService

        _nutrition_lookup_service = NutritionLookupService(
            food_ref_repo=get_async_food_reference_repository(),
            ingredient_nutrition_resolver=get_ingredient_nutrition_resolver(),
            generation_service=MealGenerationService(),
            redis_client=_redis_client,
        )
    return _nutrition_lookup_service


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
