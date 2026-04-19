"""
Event bus dependency for FastAPI with proper type registrations.
"""

from typing import Optional

from src.app.commands.daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand,
)
from src.app.commands.ingredient import RecognizeIngredientCommand

# Import all commands
from src.app.commands.meal import (
    AnalyzeMealImageByUrlCommand,
    UploadMealImageImmediatelyCommand,
    EditMealCommand,
    AddCustomIngredientCommand,
    DeleteMealCommand,
)
from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand
from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.app.commands.meal_suggestion import (
    GenerateMealSuggestionsCommand,
    SaveMealSuggestionCommand,
)
from src.app.commands.notification import (
    RegisterFcmTokenCommand,
    DeleteFcmTokenCommand,
    UpdateNotificationPreferencesCommand,
)
from src.app.commands.user import (
    SaveUserOnboardingCommand,
    CompleteOnboardingCommand,
    DeleteUserCommand,
    UpdateCustomMacrosCommand,
    UpdateLanguageCommand,
    UpdateTimezoneCommand,
)
from src.app.commands.user.sync_user_command import (
    SyncUserCommand,
    UpdateUserLastAccessedCommand,
)
from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
from src.app.events.meal import MealImageUploadedEvent

# Import all command handlers from module
from src.app.handlers.command_handlers import (
    EditMealCommandHandler,
    AddCustomIngredientCommandHandler,
    DeleteMealCommandHandler,
    SaveUserOnboardingCommandHandler,
    SyncUserCommandHandler,
    UpdateUserLastAccessedCommandHandler,
    CompleteOnboardingCommandHandler,
    DeleteUserCommandHandler,
    GenerateDailyMealSuggestionsCommandHandler,
    GenerateSingleMealCommandHandler,
    CreateManualMealCommandHandler,
    UpdateUserMetricsCommandHandler,
    AnalyzeMealImageByUrlHandler,
    UpdateCustomMacrosCommandHandler,
    UploadMealImageImmediatelyHandler,
    GenerateMealSuggestionsCommandHandler,
    SaveMealSuggestionCommandHandler,
    ParseMealTextHandler,
)

# Ingredient handlers
from src.app.handlers.command_handlers import (
    RecognizeIngredientCommandHandler,
)
from src.app.handlers.command_handlers import (
    RegisterFcmTokenCommandHandler,
    DeleteFcmTokenCommandHandler,
    UpdateLanguageCommandHandler,
    UpdateNotificationPreferencesCommandHandler,
    UpdateTimezoneCommandHandler,
)

# Saved suggestion handlers
from src.app.handlers.command_handlers import (
    SaveSuggestionCommandHandler,
    DeleteSavedSuggestionCommandHandler,
)
from src.app.commands.saved_suggestion import (
    SaveSuggestionCommand,
    DeleteSavedSuggestionCommand,
)
from src.app.queries.saved_suggestion import GetSavedSuggestionsQuery
from src.app.handlers.query_handlers import GetSavedSuggestionsQueryHandler
from src.app.commands.cheat_day import MarkCheatDayCommand, UnmarkCheatDayCommand
from src.app.queries.cheat_day import GetCheatDaysQuery
from src.app.handlers.command_handlers.mark_cheat_day_command_handler import (
    MarkCheatDayCommandHandler,
)
from src.app.handlers.command_handlers.unmark_cheat_day_command_handler import (
    UnmarkCheatDayCommandHandler,
)
from src.app.handlers.query_handlers.get_cheat_days_query_handler import (
    GetCheatDaysQueryHandler,
)

# Import event handlers
from src.app.handlers.event_handlers.meal_analysis_event_handler import (
    MealAnalysisEventHandler,
)
from src.app.handlers.query_handlers import (
    GetNotificationPreferencesQueryHandler,
)

# Import all query handlers from module
from src.app.handlers.query_handlers import (
    GetUserTdeeQueryHandler,
    PreviewTdeeQueryHandler,
    SearchFoodsQueryHandler,
    GetFoodDetailsQueryHandler,
    LookupBarcodeQueryHandler,
    GetMealByIdQueryHandler,
    GetDailyMacrosQueryHandler,
    GetWeeklyBudgetQueryHandler,
    GetUserProfileQueryHandler,
    GetUserByFirebaseUidQueryHandler,
    GetUserOnboardingStatusQueryHandler,
    GetDailyActivitiesQueryHandler,
    GetMealsByDateQueryHandler,
    GetMealSuggestionsForProfileQueryHandler,
    GetSingleMealForProfileQueryHandler,
    GetMealPlanningSummaryQueryHandler,
    GetUserMetricsQueryHandler,
    GetStreakQueryHandler,
    GetDailyBreakdownQueryHandler,
)
from src.app.queries.activity import GetDailyActivitiesQuery
from src.app.queries.daily_meal import (
    GetMealSuggestionsForProfileQuery,
    GetSingleMealForProfileQuery,
    GetMealPlanningSummaryQuery,
)
from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery
from src.app.queries.food.search_foods_query import SearchFoodsQuery

# Import all queries
from src.app.queries.meal import (
    GetMealByIdQuery,
    GetDailyMacrosQuery,
    GetMealsByDateQuery,
    GetStreakQuery,
    GetDailyBreakdownQuery,
)
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.app.queries.notification import GetNotificationPreferencesQuery
from src.app.queries.tdee import GetUserTdeeQuery, PreviewTdeeQuery
from src.app.queries.user import GetUserProfileQuery, GetUserMetricsQuery
from src.app.queries.user.get_user_by_firebase_uid_query import (
    GetUserByFirebaseUidQuery,
)
from src.app.queries.user.get_user_onboarding_status_query import (
    GetUserOnboardingStatusQuery,
)
from src.infra.event_bus import PyMediatorEventBus, EventBus

# Singleton event buses
_food_search_event_bus: Optional[EventBus] = None
_configured_event_bus: Optional[EventBus] = None


def get_food_search_event_bus() -> EventBus:
    """
    Get a lightweight event bus for food search operations (singleton).

    This event bus only registers food-related handlers and does NOT
    initialize heavy services like Cloudinary, Gemini, etc.

    Returns:
        EventBus: Lightweight event bus for food search
    """
    global _food_search_event_bus
    if _food_search_event_bus is not None:
        return _food_search_event_bus

    from src.api.base_dependencies import (
        get_food_cache_service,
        get_food_data_service,
        get_food_mapping_service,
        get_open_food_facts_service_instance,
        get_fat_secret_service_instance,
        get_food_reference_repository,
    )

    from src.infra.adapters.meal_generation_service import MealGenerationService
    from src.domain.services.food_search_translation_service import (
        FoodSearchTranslationService,
    )
    from src.infra.adapters.nutritionix_service import get_nutritionix_service
    from src.infra.adapters.brave_search_nutrition_service import (
        get_brave_search_nutrition_service,
    )
    from src.domain.services.meal_suggestion.macro_validation_service import (
        MacroValidationService,
    )

    event_bus = PyMediatorEventBus()

    # Only register food-related handlers (lightweight)
    food_cache_service = get_food_cache_service()
    food_data_service = get_food_data_service()
    food_mapping_service = get_food_mapping_service()
    open_food_facts_service = get_open_food_facts_service_instance()
    fat_secret_service = get_fat_secret_service_instance()
    food_reference_repository = get_food_reference_repository()

    # Translation service for localized food search
    meal_generation_service = MealGenerationService()
    food_translation_service = FoodSearchTranslationService(meal_generation_service)

    # Barcode cascade: Nutritionix + Brave Search (optional — None if keys not set)
    nutritionix_service = get_nutritionix_service()
    macro_validation_service = MacroValidationService()
    brave_search_service = get_brave_search_nutrition_service(
        meal_generation_service=meal_generation_service,
        macro_validation_service=macro_validation_service,
    )

    event_bus.register_handler(
        SearchFoodsQuery,
        SearchFoodsQueryHandler(
            food_cache_service,
            food_mapping_service,
            fat_secret_service=fat_secret_service,
            translation_service=food_translation_service,
        ),
    )
    event_bus.register_handler(
        GetFoodDetailsQuery,
        GetFoodDetailsQueryHandler(
            food_data_service, food_cache_service, food_mapping_service
        ),
    )
    event_bus.register_handler(
        LookupBarcodeQuery,
        LookupBarcodeQueryHandler(
            open_food_facts_service=open_food_facts_service,
            fat_secret_service=fat_secret_service,
            food_reference_repository=food_reference_repository,
            translation_service=food_translation_service,
            nutritionix_service=nutritionix_service,
            brave_search_service=brave_search_service,
            meal_generation_service=meal_generation_service,
            macro_validation_service=macro_validation_service,
        ),
    )

    _food_search_event_bus = event_bus
    return _food_search_event_bus


def get_configured_event_bus() -> EventBus:
    """
    Get a singleton event bus with all handlers configured.

    This is now a singleton to prevent memory leaks from creating new event buses
    and dynamically generated handler classes on every request.

    Handlers use ScopedSession to access the current request's database session,
    ensuring proper isolation while allowing the event bus to be reused.

    Returns:
        EventBus: Singleton event bus instance
    """
    global _configured_event_bus

    if _configured_event_bus is not None:
        return _configured_event_bus

    # Get singleton services (these are safe to reuse)
    from src.api.base_dependencies import (
        get_image_store,
        get_vision_service,
        get_gpt_parser,
        get_food_cache_service,
        get_food_data_service,
        get_food_mapping_service,
        get_fat_secret_service_instance,
        get_cache_service,
        get_suggestion_orchestration_service,
        get_meal_translation_service,
    )

    image_store = get_image_store()
    vision_service = get_vision_service()
    gpt_parser = get_gpt_parser()
    food_cache_service = get_food_cache_service()
    food_data_service = get_food_data_service()
    food_mapping_service = get_food_mapping_service()
    fat_secret_service = get_fat_secret_service_instance()
    cache_service = get_cache_service()
    suggestion_service = get_suggestion_orchestration_service()

    from src.infra.database.uow import UnitOfWork

    event_bus = PyMediatorEventBus()

    # Register meal command handlers
    # Handlers receive UnitOfWork (concrete) and event_bus at the composition root
    meal_translation_service = get_meal_translation_service()
    event_bus.register_handler(
        UploadMealImageImmediatelyCommand,
        UploadMealImageImmediatelyHandler(
            uow=UnitOfWork(),
            event_bus=event_bus,
            image_store=image_store,
            vision_service=vision_service,
            gpt_parser=gpt_parser,
            meal_translation_service=meal_translation_service,
        ),
    )
    event_bus.register_handler(
        AnalyzeMealImageByUrlCommand,
        AnalyzeMealImageByUrlHandler(
            uow=UnitOfWork(),
            event_bus=event_bus,
            vision_service=vision_service,
            gpt_parser=gpt_parser,
            meal_translation_service=meal_translation_service,
        ),
    )

    # Register meal edit command handlers
    event_bus.register_handler(
        EditMealCommand,
        EditMealCommandHandler(
            uow=UnitOfWork(),
            event_bus=event_bus,
        ),
    )

    event_bus.register_handler(
        AddCustomIngredientCommand,
        AddCustomIngredientCommandHandler(
            uow=UnitOfWork(),
            event_bus=event_bus,
        ),
    )

    event_bus.register_handler(
        DeleteMealCommand,
        DeleteMealCommandHandler(
            uow=UnitOfWork(),
            event_bus=event_bus,
        ),
    )

    event_bus.register_handler(
        CreateManualMealCommand,
        CreateManualMealCommandHandler(
            uow=UnitOfWork(),
            event_bus=event_bus,
        ),
    )

    # Register meal text parsing command handler
    event_bus.register_handler(
        ParseMealTextCommand,
        ParseMealTextHandler(),
    )

    # Register food database query handlers
    event_bus.register_handler(
        SearchFoodsQuery,
        SearchFoodsQueryHandler(
            food_cache_service,
            food_mapping_service,
            fat_secret_service=fat_secret_service,
        ),
    )
    event_bus.register_handler(
        GetFoodDetailsQuery,
        GetFoodDetailsQueryHandler(
            food_data_service, food_cache_service, food_mapping_service
        ),
    )

    # Register meal query handlers
    # These handlers now use UnitOfWork internally for fresh sessions
    event_bus.register_handler(GetMealByIdQuery, GetMealByIdQueryHandler())
    event_bus.register_handler(
        GetDailyMacrosQuery,
        GetDailyMacrosQueryHandler(
            cache_service=cache_service,
        ),
    )
    event_bus.register_handler(
        GetWeeklyBudgetQuery,
        GetWeeklyBudgetQueryHandler(cache_service=cache_service),
    )
    event_bus.register_handler(
        GetStreakQuery,
        GetStreakQueryHandler(cache_service=cache_service),
    )
    event_bus.register_handler(
        GetDailyBreakdownQuery,
        GetDailyBreakdownQueryHandler(cache_service=cache_service),
    )

    # Register activity query handlers
    event_bus.register_handler(
        GetDailyActivitiesQuery,
        GetDailyActivitiesQueryHandler(cache_service=cache_service),
    )

    # Register daily meal handlers
    event_bus.register_handler(
        GenerateDailyMealSuggestionsCommand,
        GenerateDailyMealSuggestionsCommandHandler(),
    )
    event_bus.register_handler(
        GenerateSingleMealCommand, GenerateSingleMealCommandHandler()
    )
    event_bus.register_handler(
        GetMealSuggestionsForProfileQuery,
        GetMealSuggestionsForProfileQueryHandler(),
    )
    event_bus.register_handler(
        GetSingleMealForProfileQuery, GetSingleMealForProfileQueryHandler()
    )
    event_bus.register_handler(
        GetMealPlanningSummaryQuery, GetMealPlanningSummaryQueryHandler()
    )

    event_bus.register_handler(GetMealsByDateQuery, GetMealsByDateQueryHandler())

    # Register meal suggestion handlers
    event_bus.register_handler(
        GenerateMealSuggestionsCommand,
        GenerateMealSuggestionsCommandHandler(suggestion_service),
    )
    event_bus.register_handler(
        SaveMealSuggestionCommand,
        SaveMealSuggestionCommandHandler(uow=UnitOfWork(), event_bus=event_bus),
    )

    # Register user handlers
    event_bus.register_handler(
        SaveUserOnboardingCommand,
        SaveUserOnboardingCommandHandler(cache_service=cache_service),
    )
    event_bus.register_handler(SyncUserCommand, SyncUserCommandHandler())
    event_bus.register_handler(
        UpdateUserLastAccessedCommand, UpdateUserLastAccessedCommandHandler()
    )
    event_bus.register_handler(
        CompleteOnboardingCommand,
        CompleteOnboardingCommandHandler(cache_service=cache_service),
    )
    event_bus.register_handler(
        DeleteUserCommand, DeleteUserCommandHandler(cache_service=cache_service)
    )
    event_bus.register_handler(
        UpdateUserMetricsCommand,
        UpdateUserMetricsCommandHandler(uow=UnitOfWork(), cache_service=cache_service),
    )
    event_bus.register_handler(
        UpdateTimezoneCommand,
        UpdateTimezoneCommandHandler(),
    )
    event_bus.register_handler(
        UpdateLanguageCommand,
        UpdateLanguageCommandHandler(),
    )
    event_bus.register_handler(
        UpdateCustomMacrosCommand,
        UpdateCustomMacrosCommandHandler(cache_service=cache_service),
    )
    event_bus.register_handler(
        GetUserProfileQuery,
        GetUserProfileQueryHandler(cache_service=cache_service),
    )
    event_bus.register_handler(
        GetUserByFirebaseUidQuery, GetUserByFirebaseUidQueryHandler()
    )
    event_bus.register_handler(
        GetUserOnboardingStatusQuery, GetUserOnboardingStatusQueryHandler()
    )
    event_bus.register_handler(
        GetUserMetricsQuery, GetUserMetricsQueryHandler(cache_service=cache_service)
    )
    event_bus.register_handler(
        GetUserTdeeQuery, GetUserTdeeQueryHandler(cache_service=cache_service)
    )
    event_bus.register_handler(PreviewTdeeQuery, PreviewTdeeQueryHandler())

    # Register notification handlers
    event_bus.register_handler(
        RegisterFcmTokenCommand, RegisterFcmTokenCommandHandler()
    )
    event_bus.register_handler(DeleteFcmTokenCommand, DeleteFcmTokenCommandHandler())
    event_bus.register_handler(
        UpdateNotificationPreferencesCommand,
        UpdateNotificationPreferencesCommandHandler(cache_service=cache_service),
    )
    event_bus.register_handler(
        GetNotificationPreferencesQuery,
        GetNotificationPreferencesQueryHandler(cache_service=cache_service),
    )

    # Register ingredient recognition handler
    from src.api.base_dependencies import get_translation_service

    translation_service = get_translation_service()
    event_bus.register_handler(
        RecognizeIngredientCommand,
        RecognizeIngredientCommandHandler(
            vision_service=vision_service,
            translation_service=translation_service,
        ),
    )

    # Register cheat day handlers
    event_bus.register_handler(MarkCheatDayCommand, MarkCheatDayCommandHandler())
    event_bus.register_handler(UnmarkCheatDayCommand, UnmarkCheatDayCommandHandler())
    event_bus.register_handler(GetCheatDaysQuery, GetCheatDaysQueryHandler())

    # Register saved suggestion handlers
    event_bus.register_handler(
        SaveSuggestionCommand,
        SaveSuggestionCommandHandler(uow=UnitOfWork(), cache_service=cache_service),
    )
    event_bus.register_handler(
        DeleteSavedSuggestionCommand,
        DeleteSavedSuggestionCommandHandler(cache_service=cache_service),
    )
    event_bus.register_handler(
        GetSavedSuggestionsQuery,
        GetSavedSuggestionsQueryHandler(cache_service=cache_service),
    )

    # Register domain event subscribers
    meal_analysis_handler = MealAnalysisEventHandler(
        vision_service=vision_service,
        gpt_parser=gpt_parser,
        image_store=image_store,
        meal_translation_service=meal_translation_service,
    )
    event_bus.subscribe(MealImageUploadedEvent, meal_analysis_handler)

    # Subscribe cache invalidation handler to meal mutation events
    from src.app.events.meal.meal_cache_invalidation_required_event import (
        MealCacheInvalidationRequiredEvent,
    )
    from src.app.handlers.event_handlers.cache_invalidation_event_handler import (
        CacheInvalidationEventHandler,
    )

    if cache_service is not None:
        cache_invalidation_handler = CacheInvalidationEventHandler(cache=cache_service)
        event_bus.subscribe(
            MealCacheInvalidationRequiredEvent, cache_invalidation_handler.handle
        )

    _configured_event_bus = event_bus
    return _configured_event_bus
