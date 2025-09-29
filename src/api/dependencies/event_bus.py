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
    UploadMealImageImmediatelyCommand,
    EditMealCommand,
    AddCustomIngredientCommand,
    DeleteMealCommand,
)
from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand
from src.app.commands.meal_plan import (
    GenerateWeeklyIngredientBasedMealPlanCommand,
)
from src.app.commands.user import (
    SaveUserOnboardingCommand,
    CompleteOnboardingCommand,
)
from src.app.commands.user.update_user_goal_command import UpdateUserGoalCommand
from src.app.commands.user.sync_user_command import (
    SyncUserCommand,
    UpdateUserLastAccessedCommand,
)
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
    GenerateDailyMealSuggestionsCommandHandler,
    GenerateSingleMealCommandHandler,
    CreateManualMealCommandHandler,
    UpdateUserGoalCommandHandler,
)
from src.app.handlers.command_handlers.weekly_ingredient_based_meal_plan_command_handler import (
    GenerateWeeklyIngredientBasedMealPlanCommandHandler,
    UploadMealImageImmediatelyHandler,
)
# Import event handlers
from src.app.handlers.event_handlers.meal_analysis_event_handler import (
    MealAnalysisEventHandler,
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
    GetMealsByDateMealPlanQueryHandler,
    GetMealSuggestionsForProfileQueryHandler,
    GetSingleMealForProfileQueryHandler,
    GetMealPlanningSummaryQueryHandler,
)
from src.app.queries.activity import GetDailyActivitiesQuery
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
    GetMealPlanQuery,
    GetMealsByDateQuery as MealPlanGetMealsByDateQuery,
)
from src.app.queries.tdee import GetUserTdeeQuery
from src.app.queries.user import GetUserProfileQuery
from src.app.queries.user.get_user_by_firebase_uid_query import (
    GetUserByFirebaseUidQuery,
    GetUserOnboardingStatusQuery,
)
from src.domain.ports.food_cache_service_port import FoodCacheServicePort
from src.domain.ports.food_data_service_port import FoodDataServicePort
from src.domain.ports.food_mapping_service_port import FoodMappingServicePort
from src.infra.event_bus import PyMediatorEventBus, EventBus


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
        UploadMealImageImmediatelyCommand,
        UploadMealImageImmediatelyHandler(
            image_store=image_store,
            meal_repository=meal_repository,
            vision_service=vision_service,
            gpt_parser=gpt_parser,
        ),
    )

    # Register meal edit command handlers
    event_bus.register_handler(
        EditMealCommand,
        EditMealCommandHandler(
            meal_repository=meal_repository,
            food_service=food_data_service,
            nutrition_calculator=None  # TODO: Add nutrition calculator if needed
        ),
    )

    event_bus.register_handler(
        AddCustomIngredientCommand,
        AddCustomIngredientCommandHandler(
            meal_repository=meal_repository,
        ),
    )

    event_bus.register_handler(
        DeleteMealCommand,
        DeleteMealCommandHandler(meal_repository),
    )

    # Register manual meal creation command handler
    event_bus.register_handler(
        CreateManualMealCommand,
        CreateManualMealCommandHandler(
            meal_repository=meal_repository,
            food_data_service=food_data_service,
            mapping_service=food_mapping_service,
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
        GenerateWeeklyIngredientBasedMealPlanCommand,
        GenerateWeeklyIngredientBasedMealPlanCommandHandler(db),
    )
    event_bus.register_handler(GetMealPlanQuery, GetMealPlanQueryHandler())
    event_bus.register_handler(
        MealPlanGetMealsByDateQuery, GetMealsByDateMealPlanQueryHandler(db)
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
        UpdateUserGoalCommand, UpdateUserGoalCommandHandler(db)
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
