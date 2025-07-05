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
    get_gpt_parser
)
from src.app.handlers.command_handlers.daily_meal_command_handlers import (
    GenerateDailyMealSuggestionsCommandHandler,
    GenerateSingleMealCommandHandler
)
# Import all handlers
from src.app.handlers.command_handlers.meal_command_handlers import (
    UploadMealImageCommandHandler,
    RecalculateMealNutritionCommandHandler,
    AnalyzeMealImageCommandHandler
)
from src.app.handlers.command_handlers.meal_plan_command_handlers import (
    StartMealPlanConversationCommandHandler,
    SendConversationMessageCommandHandler,
    GenerateMealPlanCommandHandler,
    ReplaceMealInPlanCommandHandler
)
from src.app.handlers.command_handlers.tdee_command_handlers import CalculateTdeeCommandHandler
from src.app.handlers.command_handlers.upload_meal_image_immediately_handler import (
    UploadMealImageImmediatelyHandler
)
from src.app.handlers.command_handlers import (
    SaveUserOnboardingCommandHandler,
    UpdateUserProfileCommandHandler
)
from src.app.commands.daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand
)
# Import all commands
from src.app.commands.meal import (
    UploadMealImageCommand,
    RecalculateMealNutritionCommand,
    AnalyzeMealImageCommand,
    UploadMealImageImmediatelyCommand
)
from src.app.commands.meal_plan import (
    StartMealPlanConversationCommand,
    SendConversationMessageCommand,
    GenerateMealPlanCommand,
    ReplaceMealInPlanCommand
)
from src.app.commands.tdee import CalculateTdeeCommand
from src.app.commands.user import (
    SaveUserOnboardingCommand,
    UpdateUserProfileCommand
)
from src.app.queries.activity import GetDailyActivitiesQuery
from src.app.queries.daily_meal import (
    GetMealSuggestionsForProfileQuery,
    GetSingleMealForProfileQuery,
    GetMealPlanningSummaryQuery
)
# Import all queries
from src.app.queries.meal import (
    GetMealByIdQuery,
    GetMealsByDateQuery,
    GetDailyMacrosQuery,
    SearchMealsQuery
)
from src.app.queries.meal_plan import (
    GetConversationHistoryQuery,
    GetMealPlanQuery
)
from src.app.queries.tdee import (
    GetMacroTargetsQuery,
    CompareTdeeMethodsQuery
)
from src.app.queries.user import (
    GetOnboardingSectionsQuery,
    GetUserProfileQuery
)
from src.app.handlers.query_handlers.activity_query_handlers import GetDailyActivitiesQueryHandler
from src.app.handlers.query_handlers import (
    GetMealSuggestionsForProfileQueryHandler,
    GetSingleMealForProfileQueryHandler,
    GetMealPlanningSummaryQueryHandler
)
from src.app.handlers.query_handlers.meal_plan_query_handlers import (
    GetConversationHistoryQueryHandler,
    GetMealPlanQueryHandler
)
from src.app.handlers.query_handlers.meal_query_handlers import (
    GetMealByIdQueryHandler,
    GetMealsByDateQueryHandler,
    GetDailyMacrosQueryHandler,
    SearchMealsQueryHandler
)
from src.app.handlers.query_handlers.tdee_query_handlers import (
    GetMacroTargetsQueryHandler,
    CompareTdeeMethodsQueryHandler
)
from src.app.handlers.query_handlers.user_query_handlers import (
    GetOnboardingSectionsQueryHandler,
    GetUserProfileQueryHandler
)
from src.infra.event_bus import PyMediatorEventBus, EventBus


async def get_configured_event_bus(
    db: Session = Depends(get_db),
    image_store = Depends(get_image_store),
    meal_repository = Depends(get_meal_repository),
    vision_service = Depends(get_vision_service),
    gpt_parser = Depends(get_gpt_parser)
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
            vision_service=vision_service,
            gpt_parser=gpt_parser
        )
    )
    
    event_bus.register_handler(
        RecalculateMealNutritionCommand,
        RecalculateMealNutritionCommandHandler(meal_repository)
    )
    
    event_bus.register_handler(
        AnalyzeMealImageCommand,
        AnalyzeMealImageCommandHandler(
            meal_repository=meal_repository,
            vision_service=vision_service,
            gpt_parser=gpt_parser
        )
    )
    
    event_bus.register_handler(
        UploadMealImageImmediatelyCommand,
        UploadMealImageImmediatelyHandler(
            image_store=image_store,
            meal_repository=meal_repository,
            vision_service=vision_service,
            gpt_parser=gpt_parser
        )
    )
    
    # Register meal query handlers
    event_bus.register_handler(
        GetMealByIdQuery,
        GetMealByIdQueryHandler(meal_repository)
    )
    
    event_bus.register_handler(
        GetMealsByDateQuery,
        GetMealsByDateQueryHandler(meal_repository)
    )
    
    event_bus.register_handler(
        GetDailyMacrosQuery,
        GetDailyMacrosQueryHandler(meal_repository)
    )
    
    event_bus.register_handler(
        SearchMealsQuery,
        SearchMealsQueryHandler(meal_repository)
    )
    
    # Register activity query handlers
    event_bus.register_handler(
        GetDailyActivitiesQuery,
        GetDailyActivitiesQueryHandler(meal_repository)
    )
    
    # Register TDEE handlers
    event_bus.register_handler(
        CalculateTdeeCommand,
        CalculateTdeeCommandHandler()
    )
    
    event_bus.register_handler(
        GetMacroTargetsQuery,
        GetMacroTargetsQueryHandler()
    )
    
    event_bus.register_handler(
        CompareTdeeMethodsQuery,
        CompareTdeeMethodsQueryHandler()
    )
    
    # Register daily meal handlers
    event_bus.register_handler(
        GenerateDailyMealSuggestionsCommand,
        GenerateDailyMealSuggestionsCommandHandler()
    )
    
    event_bus.register_handler(
        GenerateSingleMealCommand,
        GenerateSingleMealCommandHandler()
    )
    
    event_bus.register_handler(
        GetMealSuggestionsForProfileQuery,
        GetMealSuggestionsForProfileQueryHandler(db)
    )
    
    event_bus.register_handler(
        GetSingleMealForProfileQuery,
        GetSingleMealForProfileQueryHandler(db)
    )
    
    event_bus.register_handler(
        GetMealPlanningSummaryQuery,
        GetMealPlanningSummaryQueryHandler(db)
    )
    
    # Register meal plan handlers
    event_bus.register_handler(
        StartMealPlanConversationCommand,
        StartMealPlanConversationCommandHandler()
    )
    
    event_bus.register_handler(
        SendConversationMessageCommand,
        SendConversationMessageCommandHandler()
    )
    
    event_bus.register_handler(
        GenerateMealPlanCommand,
        GenerateMealPlanCommandHandler()
    )
    
    event_bus.register_handler(
        ReplaceMealInPlanCommand,
        ReplaceMealInPlanCommandHandler()
    )
    
    event_bus.register_handler(
        GetConversationHistoryQuery,
        GetConversationHistoryQueryHandler()
    )
    
    event_bus.register_handler(
        GetMealPlanQuery,
        GetMealPlanQueryHandler()
    )
    
    # Register user handlers
    event_bus.register_handler(
        SaveUserOnboardingCommand,
        SaveUserOnboardingCommandHandler(db)
    )
    
    event_bus.register_handler(
        UpdateUserProfileCommand,
        UpdateUserProfileCommandHandler(db)
    )
    
    event_bus.register_handler(
        GetOnboardingSectionsQuery,
        GetOnboardingSectionsQueryHandler()
    )
    
    event_bus.register_handler(
        GetUserProfileQuery,
        GetUserProfileQueryHandler(db)
    )
    
    return event_bus