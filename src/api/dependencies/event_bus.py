"""
Event bus dependency for FastAPI with proper type registrations.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.api.base_dependencies import (
    get_db,
    get_image_store,
    get_meal_repository,
    get_vision_service,
    get_gpt_parser,
    get_food_data_service,
    get_food_cache_service,
    get_food_mapping_service,
)
from src.app.commands.daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand,
)
# Import all commands
from src.app.commands.meal import (
    UploadMealImageCommand,
    RecalculateMealNutritionCommand,
    UploadMealImageImmediatelyCommand,
)
from src.app.commands.meal_plan import (
    StartMealPlanConversationCommand,
    SendConversationMessageCommand,
    GenerateDailyMealPlanCommand,
    GenerateIngredientBasedMealPlanCommand,
    GenerateWeeklyIngredientBasedMealPlanCommand,
    ReplaceMealInPlanCommand,
)
from src.app.commands.user import (
    SaveUserOnboardingCommand,
    CompleteOnboardingCommand,
)
from src.app.commands.user.sync_user_command import (
    SyncUserCommand,
    UpdateUserLastAccessedCommand,
)
from src.app.events.meal import MealImageUploadedEvent
from src.app.handlers.command_handlers.daily_meal_command_handlers import (
    GenerateDailyMealSuggestionsCommandHandler,
    GenerateSingleMealCommandHandler,
)
from src.app.handlers.command_handlers.ingredient_based_meal_plan_command_handler import (
    GenerateIngredientBasedMealPlanCommandHandler,
)
# Import all handlers
from src.app.handlers.command_handlers.meal_command_handlers import (
    UploadMealImageCommandHandler,
    RecalculateMealNutritionCommandHandler,
)
from src.app.handlers.command_handlers.meal_plan_command_handlers import (
    StartMealPlanConversationCommandHandler,
    SendConversationMessageCommandHandler,
    GenerateDailyMealPlanCommandHandler,
    ReplaceMealInPlanCommandHandler,
)
from src.app.handlers.command_handlers.upload_meal_image_immediately_handler import (
    UploadMealImageImmediatelyHandler,
)
from src.app.handlers.command_handlers.user_command_handlers import (
    SaveUserOnboardingCommandHandler,
    SyncUserCommandHandler,
    UpdateUserLastAccessedCommandHandler,
    CompleteOnboardingCommandHandler,
)
from src.app.handlers.command_handlers.weekly_ingredient_based_meal_plan_command_handler import (
    GenerateWeeklyIngredientBasedMealPlanCommandHandler,
)
from src.app.handlers.event_handlers.meal_analysis_event_handler import (
    MealAnalysisEventHandler,
)
from src.app.handlers.query_handlers.activity_query_handlers import (
    GetDailyActivitiesQueryHandler,
)
from src.app.handlers.query_handlers.daily_meal_query_handlers import (
    GetMealSuggestionsForProfileQueryHandler,
    GetSingleMealForProfileQueryHandler,
    GetMealPlanningSummaryQueryHandler,
)
from src.app.handlers.query_handlers.meal_plan_query_handlers import (
    GetConversationHistoryQueryHandler,
    GetMealPlanQueryHandler,
    GetMealsByDateQueryHandler as MealPlanGetMealsByDateQueryHandler,
)
from src.app.handlers.query_handlers.meal_query_handlers import (
    GetMealByIdQueryHandler,
    GetMealsByDateQueryHandler,
    GetDailyMacrosQueryHandler,
)
from src.app.handlers.query_handlers.tdee_query_handlers import (
    GetUserTdeeQueryHandler,
)
from src.app.handlers.query_handlers.user_query_handlers import (
    GetUserProfileQueryHandler,
    GetUserByFirebaseUidQueryHandler,
    GetUserOnboardingStatusQueryHandler,
)
from src.app.handlers.query_handlers.food_query_handlers import (
    SearchFoodsQueryHandler,
    GetFoodDetailsQueryHandler,
)
from src.app.queries.activity import GetDailyActivitiesQuery
from src.app.queries.daily_meal import (
    GetMealSuggestionsForProfileQuery,
    GetSingleMealForProfileQuery,
    GetMealPlanningSummaryQuery,
)
# Import all queries
from src.app.queries.meal import (
    GetMealByIdQuery,
    GetMealsByDateQuery,
    GetDailyMacrosQuery,
)
from src.app.queries.meal_plan import (
    GetConversationHistoryQuery,
    GetMealPlanQuery,
    GetMealsByDateQuery as MealPlanGetMealsByDateQuery,
)
from src.app.queries.tdee import GetUserTdeeQuery
from src.app.queries.user import GetUserProfileQuery
from src.app.queries.user.get_user_by_firebase_uid_query import (
    GetUserByFirebaseUidQuery,
    GetUserOnboardingStatusQuery,
)
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery
from src.infra.event_bus import PyMediatorEventBus, EventBus
from src.domain.ports.food_data_service_port import FoodDataServicePort
from src.domain.ports.food_cache_service_port import FoodCacheServicePort
from src.domain.ports.food_mapping_service_port import FoodMappingServicePort


async def get_configured_event_bus(
    db: Session = Depends(get_db),
    image_store = Depends(get_image_store),
    meal_repository = Depends(get_meal_repository),
    vision_service = Depends(get_vision_service),
    gpt_parser = Depends(get_gpt_parser),
    food_data_service: FoodDataServicePort = Depends(get_food_data_service),
    food_cache_service: FoodCacheServicePort = Depends(get_food_cache_service),
    food_mapping_service: FoodMappingServicePort = Depends(get_food_mapping_service),
) -> EventBus:
    """
    Get an event bus with all handlers configured.
    """
    event_bus = PyMediatorEventBus()

    # Register meal command handlers
    event_bus.register_handler(
        UploadMealImageCommand,
        UploadMealImageCommandHandler(
            image_store=image_store,
            meal_repository=meal_repository,
        ),
    )

    event_bus.register_handler(
        RecalculateMealNutritionCommand,
        RecalculateMealNutritionCommandHandler(meal_repository),
    )

    event_bus.register_handler(
        UploadMealImageImmediatelyCommand,
        UploadMealImageImmediatelyHandler(
            image_store=image_store,
            meal_repository=meal_repository,
            vision_service=vision_service,
            gpt_parser=gpt_parser,
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
    event_bus.register_handler(
        GetMealByIdQuery, GetMealByIdQueryHandler(meal_repository)
    )
    event_bus.register_handler(
        GetMealsByDateQuery, GetMealsByDateQueryHandler(meal_repository)
    )
    event_bus.register_handler(
        GetDailyMacrosQuery, GetDailyMacrosQueryHandler(meal_repository, db)
    )

    # Register activity query handlers
    event_bus.register_handler(
        GetDailyActivitiesQuery, GetDailyActivitiesQueryHandler(meal_repository)
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
        GetMealSuggestionsForProfileQueryHandler(db),
    )
    event_bus.register_handler(
        GetSingleMealForProfileQuery, GetSingleMealForProfileQueryHandler(db)
    )
    event_bus.register_handler(
        GetMealPlanningSummaryQuery, GetMealPlanningSummaryQueryHandler(db)
    )

    # Register meal plan handlers
    event_bus.register_handler(
        StartMealPlanConversationCommand, StartMealPlanConversationCommandHandler()
    )
    event_bus.register_handler(
        SendConversationMessageCommand, SendConversationMessageCommandHandler()
    )
    event_bus.register_handler(
        GenerateDailyMealPlanCommand, GenerateDailyMealPlanCommandHandler(db)
    )
    event_bus.register_handler(
        GenerateIngredientBasedMealPlanCommand,
        GenerateIngredientBasedMealPlanCommandHandler(db),
    )
    event_bus.register_handler(
        GenerateWeeklyIngredientBasedMealPlanCommand,
        GenerateWeeklyIngredientBasedMealPlanCommandHandler(db),
    )
    event_bus.register_handler(
        ReplaceMealInPlanCommand, ReplaceMealInPlanCommandHandler()
    )
    event_bus.register_handler(
        GetConversationHistoryQuery, GetConversationHistoryQueryHandler()
    )
    event_bus.register_handler(GetMealPlanQuery, GetMealPlanQueryHandler())
    event_bus.register_handler(
        MealPlanGetMealsByDateQuery, MealPlanGetMealsByDateQueryHandler(db)
    )

    # Register user handlers
    event_bus.register_handler(
        SaveUserOnboardingCommand, SaveUserOnboardingCommandHandler(db)
    )
    event_bus.register_handler(SyncUserCommand, SyncUserCommandHandler(db))
    event_bus.register_handler(
        UpdateUserLastAccessedCommand, UpdateUserLastAccessedCommandHandler(db)
    )
    event_bus.register_handler(
        CompleteOnboardingCommand, CompleteOnboardingCommandHandler(db)
    )
    event_bus.register_handler(
        GetUserProfileQuery, GetUserProfileQueryHandler(db)
    )
    event_bus.register_handler(
        GetUserByFirebaseUidQuery, GetUserByFirebaseUidQueryHandler(db)
    )
    event_bus.register_handler(
        GetUserOnboardingStatusQuery, GetUserOnboardingStatusQueryHandler(db)
    )
    event_bus.register_handler(GetUserTdeeQuery, GetUserTdeeQueryHandler(db))

    # Register domain event subscribers
    meal_analysis_handler = MealAnalysisEventHandler(
        meal_repository=meal_repository,
        vision_service=vision_service,
        gpt_parser=gpt_parser,
        image_store=image_store,
    )
    event_bus.subscribe(
        MealImageUploadedEvent, meal_analysis_handler.handle_meal_image_uploaded
    )

    return event_bus
