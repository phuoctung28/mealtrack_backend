"""
GenerateDailyMealPlanCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.meal_plan.generate_daily_meal_plan_command import GenerateDailyMealPlanCommand
from src.app.events.base import EventHandler, handles
from src.app.handlers.shared.meal_plan_persistence_service import MealPlanPersistenceService
from src.app.handlers.shared.user_profile_service import UserProfileService
from src.domain.model.meal_plan import PlanDuration
from src.domain.services.meal_plan_orchestration_service import MealPlanOrchestrationService
from src.infra.adapters.meal_generation_service import MealGenerationService
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(GenerateDailyMealPlanCommand)
class GenerateDailyMealPlanCommandHandler(EventHandler[GenerateDailyMealPlanCommand, Dict[str, Any]]):
    """Handler for generating daily meal plans based on user profile."""

    def __init__(self,
                 db: Session = None,
                 orchestration_service: MealPlanOrchestrationService = None,
                 user_profile_service: UserProfileService = None,
                 persistence_service: MealPlanPersistenceService = None):
        self.db = db

        # Use injected services or create defaults
        if orchestration_service:
            self.orchestration_service = orchestration_service
        else:
            # Fallback to default instantiation for backward compatibility
            meal_generation_service = MealGenerationService()
            self.orchestration_service = MealPlanOrchestrationService(meal_generation_service)

        self.user_profile_service = user_profile_service or (UserProfileService(db) if db else None)
        self.persistence_service = persistence_service or (MealPlanPersistenceService(db) if db else None)

    def set_dependencies(self,
                        db: Session = None,
                        orchestration_service: MealPlanOrchestrationService = None,
                        user_profile_service: UserProfileService = None,
                        persistence_service: MealPlanPersistenceService = None):
        """Set dependencies for dependency injection."""
        if db:
            self.db = db
        if orchestration_service:
            self.orchestration_service = orchestration_service
        if user_profile_service:
            self.user_profile_service = user_profile_service
        elif db:
            self.user_profile_service = UserProfileService(db)
        if persistence_service:
            self.persistence_service = persistence_service
        elif db:
            self.persistence_service = MealPlanPersistenceService(db)

    async def handle(self, command: GenerateDailyMealPlanCommand) -> Dict[str, Any]:
        """Generate a daily meal plan based on user profile."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Get user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == command.user_id,
            UserProfile.is_current == True
        ).first()

        if not profile:
            raise ResourceNotFoundException(
                message="User profile not found",
                details={"user_id": command.user_id}
            )

        # Import the command handler to calculate TDEE
        # Calculate TDEE using the proper query handler
        from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler
        from src.app.queries.tdee import GetUserTdeeQuery

        tdee_handler = GetUserTdeeQueryHandler(self.db)
        tdee_query = GetUserTdeeQuery(user_id=profile.user_id)
        tdee_result = await tdee_handler.handle(tdee_query)

        # Get user profile data using shared service
        user_data = self.user_profile_service.get_user_profile_or_defaults(command.user_id)
        user_data['user_id'] = command.user_id

        # Generate daily meal plan using orchestration service
        result = self.orchestration_service.generate_daily_plan(user_data)

        logger.info(f"Generated daily meal plan for user {command.user_id} with {len(result['meals'])} meals")

        # Save to database using shared service
        if self.persistence_service:
            user_preferences = self.user_profile_service.create_user_preferences_from_data(
                user_data, PlanDuration.DAILY
            )
            plan_id = self.persistence_service.save_daily_meal_plan(
                result, user_preferences, command.user_id
            )
            result["plan_id"] = plan_id
            logger.info(f"Saved meal plan {plan_id} to database")

        return result
