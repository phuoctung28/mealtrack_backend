"""
Event bus dependency for FastAPI with proper type registrations.
"""
from typing import Optional

from src.app.commands.chat import (
    CreateThreadCommand,
    SendMessageCommand,
    DeleteThreadCommand,
)
from src.app.commands.daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand,
)
from src.app.commands.ingredient import RecognizeIngredientCommand
# Import all commands
from src.app.commands.meal import (
    UploadMealImageImmediatelyCommand,
    EditMealCommand,
    AddCustomIngredientCommand,
    DeleteMealCommand,
)
from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand
from src.app.commands.meal_plan import (
    GenerateWeeklyIngredientBasedMealPlanCommand,
)
from src.app.commands.meal_suggestion import GenerateMealSuggestionsCommand, SaveMealSuggestionCommand
from src.app.commands.notification import (
    RegisterFcmTokenCommand,
    DeleteFcmTokenCommand,
    UpdateNotificationPreferencesCommand,
)
from src.app.commands.user import (
    SaveUserOnboardingCommand,
    CompleteOnboardingCommand,
    DeleteUserCommand,
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
    UploadMealImageImmediatelyHandler,
    GenerateWeeklyIngredientBasedMealPlanCommandHandler,
    GenerateMealSuggestionsCommandHandler,
    SaveMealSuggestionCommandHandler,
)
# Ingredient handlers
from src.app.handlers.command_handlers import (
    RecognizeIngredientCommandHandler,
)
from src.app.handlers.command_handlers import (
    RegisterFcmTokenCommandHandler,
    DeleteFcmTokenCommandHandler,
    UpdateNotificationPreferencesCommandHandler,
)
# Chat handlers
from src.app.handlers.command_handlers.chat import (
    CreateThreadCommandHandler,
    SendMessageCommandHandler,
    DeleteThreadCommandHandler,
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
    SearchFoodsQueryHandler,
    GetFoodDetailsQueryHandler,
    GetMealByIdQueryHandler,
    GetDailyMacrosQueryHandler,
    GetUserProfileQueryHandler,
    GetUserByFirebaseUidQueryHandler,
    GetUserOnboardingStatusQueryHandler,
    GetDailyActivitiesQueryHandler,
    GetMealPlanQueryHandler,
    GetMealsFromPlanByDateQueryHandler,
    GetMealsByDateQueryHandler,
    GetMealSuggestionsForProfileQueryHandler,
    GetSingleMealForProfileQueryHandler,
    GetMealPlanningSummaryQueryHandler,
    GetUserMetricsQueryHandler,
)
from src.app.handlers.query_handlers.chat import (
    GetThreadsQueryHandler,
    GetThreadQueryHandler,
    GetMessagesQueryHandler,
)
from src.app.queries.activity import GetDailyActivitiesQuery
from src.app.queries.chat import (
    GetThreadsQuery,
    GetThreadQuery,
    GetMessagesQuery,
)
from src.app.queries.daily_meal import (
    GetMealSuggestionsForProfileQuery,
    GetSingleMealForProfileQuery,
    GetMealPlanningSummaryQuery,
)
from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery
from src.app.queries.food.search_foods_query import SearchFoodsQuery
# Import all queries
from src.app.queries.meal import (
    GetMealByIdQuery,
    GetDailyMacrosQuery,
)
from src.app.queries.meal_plan import (
    GetMealsFromPlanByDateQuery,
    GetMealPlanQuery,
    GetMealsByDateQuery,
)
from src.app.queries.notification import GetNotificationPreferencesQuery
from src.app.queries.tdee import GetUserTdeeQuery
from src.app.queries.user import GetUserProfileQuery, GetUserMetricsQuery
from src.app.queries.user.get_user_by_firebase_uid_query import GetUserByFirebaseUidQuery
from src.app.queries.user.get_user_onboarding_status_query import GetUserOnboardingStatusQuery
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
        get_food_data_service,
        get_food_cache_service,
        get_food_mapping_service,
    )

    event_bus = PyMediatorEventBus()

    # Only register food-related handlers (lightweight)
    food_data_service = get_food_data_service()
    food_cache_service = get_food_cache_service()
    food_mapping_service = get_food_mapping_service()

    event_bus.register_handler(
        SearchFoodsQuery,
        SearchFoodsQueryHandler(
            food_data_service, food_cache_service, food_mapping_service
        ),
    )
    event_bus.register_handler(
        GetFoodDetailsQuery,
        GetFoodDetailsQueryHandler(
            food_data_service, food_cache_service, food_mapping_service
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
        get_food_data_service,
        get_food_cache_service,
        get_food_mapping_service,
        get_cache_service,
        get_ai_chat_service,
        get_suggestion_orchestration_service,
    )
    
    image_store = get_image_store()
    vision_service = get_vision_service()
    gpt_parser = get_gpt_parser()
    food_data_service = get_food_data_service()
    food_cache_service = get_food_cache_service()
    food_mapping_service = get_food_mapping_service()
    cache_service = get_cache_service()
    ai_chat_service = get_ai_chat_service()
    suggestion_service = get_suggestion_orchestration_service()
    
    event_bus = PyMediatorEventBus()

    # Create meal repository early (needed by multiple handlers)
    from src.infra.repositories.meal_repository import MealRepository
    from src.infra.database.config import ScopedSession
    meal_repository = MealRepository(ScopedSession())

    # Register meal command handlers
    # Note: Handlers now use ScopedSession internally instead of receiving db in constructor
    event_bus.register_handler(
        UploadMealImageImmediatelyCommand,
        UploadMealImageImmediatelyHandler(
            image_store=image_store,
            vision_service=vision_service,
            gpt_parser=gpt_parser,
            cache_service=cache_service,
        ),
    )

    # Register meal edit command handlers
    event_bus.register_handler(
        EditMealCommand,
        EditMealCommandHandler(
            meal_repository=meal_repository,
            food_service=food_data_service,
            nutrition_calculator=None,  # TODO: Add nutrition calculator if needed
            cache_service=cache_service,
        ),
    )

    event_bus.register_handler(
        AddCustomIngredientCommand,
        AddCustomIngredientCommandHandler(
            cache_service=cache_service,
        ),
    )

    event_bus.register_handler(
        DeleteMealCommand,
        DeleteMealCommandHandler(
            cache_service=cache_service,
        ),
    )

    # Register manual meal creation command handler
    event_bus.register_handler(
        CreateManualMealCommand,
        CreateManualMealCommandHandler(
            food_data_service=food_data_service,
            mapping_service=food_mapping_service,
            cache_service=cache_service,
        ),
    )

    # Register food database query handlers
    event_bus.register_handler(
        SearchFoodsQuery,
        SearchFoodsQueryHandler(
            food_data_service, food_cache_service, food_mapping_service
        ),
    )
    event_bus.register_handler(
        GetFoodDetailsQuery,
        GetFoodDetailsQueryHandler(
            food_data_service, food_cache_service, food_mapping_service
        ),
    )

    # Register meal query handlers
    # meal_repository already created above
    event_bus.register_handler(
        GetMealByIdQuery, GetMealByIdQueryHandler(meal_repository=meal_repository)
    )
    event_bus.register_handler(
        GetDailyMacrosQuery,
        GetDailyMacrosQueryHandler(
            meal_repository=meal_repository,
            cache_service=cache_service,
        ),
    )

    # Register activity query handlers
    event_bus.register_handler(
        GetDailyActivitiesQuery, GetDailyActivitiesQueryHandler()
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

    # Register meal plan handlers
    event_bus.register_handler(
        GenerateWeeklyIngredientBasedMealPlanCommand,
        GenerateWeeklyIngredientBasedMealPlanCommandHandler(),
    )
    event_bus.register_handler(GetMealPlanQuery, GetMealPlanQueryHandler())
    event_bus.register_handler(
        GetMealsFromPlanByDateQuery, GetMealsFromPlanByDateQueryHandler()
    )
    event_bus.register_handler(
        GetMealsByDateQuery, GetMealsByDateQueryHandler()
    )
    
    # Register meal suggestion handlers
    event_bus.register_handler(
        GenerateMealSuggestionsCommand,
        GenerateMealSuggestionsCommandHandler(suggestion_service),
    )
    event_bus.register_handler(
        SaveMealSuggestionCommand,
        SaveMealSuggestionCommandHandler(),
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
        DeleteUserCommand, DeleteUserCommandHandler()
    )
    event_bus.register_handler(
        UpdateUserMetricsCommand,
        UpdateUserMetricsCommandHandler(cache_service=cache_service),
    )
    event_bus.register_handler(
        GetUserProfileQuery,
        GetUserProfileQueryHandler(),
    )
    event_bus.register_handler(
        GetUserByFirebaseUidQuery, GetUserByFirebaseUidQueryHandler()
    )
    event_bus.register_handler(
        GetUserOnboardingStatusQuery, GetUserOnboardingStatusQueryHandler()
    )
    event_bus.register_handler(
        GetUserMetricsQuery, GetUserMetricsQueryHandler()
    )
    event_bus.register_handler(GetUserTdeeQuery, GetUserTdeeQueryHandler())

    # Register notification handlers
    event_bus.register_handler(
        RegisterFcmTokenCommand,
        RegisterFcmTokenCommandHandler()
    )
    event_bus.register_handler(
        DeleteFcmTokenCommand,
        DeleteFcmTokenCommandHandler()
    )
    event_bus.register_handler(
        UpdateNotificationPreferencesCommand,
        UpdateNotificationPreferencesCommandHandler()
    )
    event_bus.register_handler(
        GetNotificationPreferencesQuery,
        GetNotificationPreferencesQueryHandler()
    )

    # Register ingredient recognition handler
    event_bus.register_handler(
        RecognizeIngredientCommand,
        RecognizeIngredientCommandHandler(vision_service=vision_service)
    )

    # Register chat handlers
    # Chat handlers use ScopedSession internally
    event_bus.register_handler(
        CreateThreadCommand,
        CreateThreadCommandHandler()
    )
    event_bus.register_handler(
        SendMessageCommand,
        SendMessageCommandHandler(ai_chat_service)
    )
    event_bus.register_handler(
        DeleteThreadCommand,
        DeleteThreadCommandHandler()
    )
    event_bus.register_handler(
        GetThreadsQuery,
        GetThreadsQueryHandler()
    )
    event_bus.register_handler(
        GetThreadQuery,
        GetThreadQueryHandler()
    )
    event_bus.register_handler(
        GetMessagesQuery,
        GetMessagesQueryHandler()
    )

    # Register domain event subscribers
    meal_analysis_handler = MealAnalysisEventHandler(
        vision_service=vision_service,
        gpt_parser=gpt_parser,
        image_store=image_store,
    )
    event_bus.subscribe(
        MealImageUploadedEvent, meal_analysis_handler
    )

    _configured_event_bus = event_bus
    return _configured_event_bus
