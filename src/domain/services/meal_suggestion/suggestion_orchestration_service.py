"""
Orchestration service for meal suggestions with full recipe support.
Handles session tracking and portion target calculation.
Generation logic: parallel_recipe_generator.py
TDEE helpers: suggestion_tdee_helpers.py
"""
import logging
import uuid
from typing import List, Optional, Tuple, Callable, Any

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.ports.meal_suggestion_repository_port import MealSuggestionRepositoryPort
from src.domain.services.meal_suggestion.macro_validation_service import MacroValidationService
from src.domain.services.meal_suggestion.nutrition_lookup_service import NutritionLookupService
from src.domain.services.meal_suggestion.parallel_recipe_generator import ParallelRecipeGenerator
from src.domain.services.meal_suggestion.suggestion_tdee_helpers import (
    get_adjusted_daily_target,
    calculate_daily_tdee,
)
from src.domain.services.meal_suggestion.translation_service import TranslationService
from src.domain.services.portion_calculation_service import PortionCalculationService
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


class SuggestionOrchestrationService:
    """
    Orchestrates meal suggestion generation with session tracking.
    Singleton in the event bus; uses ScopedSession for request isolation.
    """

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        suggestion_repo: MealSuggestionRepositoryPort,
        nutrition_lookup: NutritionLookupService,
        tdee_service: TdeeCalculationService = None,
        portion_service: PortionCalculationService = None,
        profile_provider: Optional[Callable[[str], Any]] = None,
        uow_factory: Optional[Callable[[], Any]] = None,
        meal_names_schema_class: type = None,
        discovery_meals_schema_class: type = None,
    ):
        self._generation = generation_service
        self._repo = suggestion_repo
        self._tdee_service = tdee_service or TdeeCalculationService()
        self._portion_service = portion_service or PortionCalculationService()
        self._profile_provider = profile_provider
        self._uow_factory = uow_factory

        self._recipe_generator = ParallelRecipeGenerator(
            generation_service=generation_service,
            translation_service=TranslationService(generation_service),
            macro_validator=MacroValidationService(),
            nutrition_lookup=nutrition_lookup,
            meal_names_schema_class=meal_names_schema_class,
            discovery_meals_schema_class=discovery_meals_schema_class,
        )

    async def generate_suggestions(
        self,
        user_id: str,
        meal_type: str,
        meal_portion_type: str,
        ingredients: List[str],
        cooking_time_minutes: Optional[int] = None,
        session_id: Optional[str] = None,
        language: str = "en",
        servings: int = 1,
        cooking_equipment: Optional[List[str]] = None,
        cuisine_region: Optional[str] = None,
        calorie_target_override: Optional[int] = None,
        protein_target: Optional[float] = None,
        carbs_target: Optional[float] = None,
        fat_target: Optional[float] = None,
        suggestion_count: int = 3,
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """Generate 3 suggestions, excluding meals shown in existing session if provided."""
        is_existing_session = False
        if session_id:
            try:
                session, exclude_names = await self._load_existing_session(session_id, user_id, language)
                is_existing_session = True
            except ValueError:
                logger.info(f"Session {session_id} not found, creating new session for user {user_id}")
                session, exclude_names = await self._create_new_session(
                    user_id, meal_type, meal_portion_type, ingredients, cooking_time_minutes,
                    language, servings, cooking_equipment, cuisine_region,
                    calorie_target_override, protein_target, carbs_target, fat_target,
                )
        else:
            session, exclude_names = await self._create_new_session(
                user_id, meal_type, meal_portion_type, ingredients, cooking_time_minutes,
                language, servings, cooking_equipment, cuisine_region,
                calorie_target_override, protein_target, carbs_target, fat_target,
            )

        suggestions = await self._recipe_generator.generate(
            session=session, exclude_meal_names=exclude_names, suggestion_count=suggestion_count,
        )
        session.add_shown_ids([s.id for s in suggestions])
        session.add_shown_meals([s.meal_name for s in suggestions])

        if is_existing_session:
            await self._repo.update_session(session)
        else:
            await self._repo.save_session(session)
        await self._repo.save_suggestions(suggestions)
        return session, suggestions

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    async def _load_existing_session(
        self, session_id: str, user_id: str, language: str
    ) -> Tuple[SuggestionSession, List[str]]:
        session = await self._repo.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found or expired. Creating new for user {user_id}")
            raise ValueError(f"Session {session_id} not found")
        if session.user_id != user_id:
            logger.warning(f"Session {session_id} user mismatch: expected {user_id}, got {session.user_id}")
            raise ValueError(f"Session {session_id} belongs to a different user")
        if session.language != language:
            logger.info(f"Updating session language: {session.language} -> {language}")
            session.language = language
        logger.info(f"Regenerating for session {session_id}, excluding {len(session.shown_meal_names)} meals")
        return session, session.shown_meal_names

    async def _create_new_session(
        self,
        user_id: str,
        meal_type: str,
        meal_portion_type: str,
        ingredients: List[str],
        cooking_time_minutes: Optional[int] = None,
        language: str = "en",
        servings: int = 1,
        cooking_equipment: Optional[List[str]] = None,
        cuisine_region: Optional[str] = None,
        calorie_target_override: Optional[int] = None,
        protein_target: Optional[float] = None,
        carbs_target: Optional[float] = None,
        fat_target: Optional[float] = None,
    ) -> Tuple[SuggestionSession, List[str]]:
        if not self._profile_provider:
            raise RuntimeError("Profile provider not configured for SuggestionOrchestrationService")
        profile = self._profile_provider(user_id)
        if not profile:
            raise ValueError(f"User {user_id} profile not found")

        if self._uow_factory:
            uow_ctx = self._uow_factory()
            with uow_ctx as uow:
                daily_tdee = await get_adjusted_daily_target(self._tdee_service, user_id, profile, uow=uow)
        else:
            daily_tdee = await get_adjusted_daily_target(self._tdee_service, user_id, profile)
        meals_per_day = getattr(profile, "meals_per_day", 3)

        if calorie_target_override:
            target_calories = calorie_target_override * servings
        else:
            portion_target = self._portion_service.get_target_for_meal_type(
                meal_type=meal_portion_type,
                daily_target=int(daily_tdee),
                meals_per_day=meals_per_day,
            )
            target_calories = portion_target.target_calories * servings

        session = SuggestionSession(
            id=f"session_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            meal_type=meal_type,
            meal_portion_type=meal_portion_type,
            target_calories=target_calories,
            ingredients=ingredients,
            cooking_time_minutes=cooking_time_minutes,
            servings=servings,
            language=language,
            # Skip user's dietary_preferences from onboarding for now.
            # Allergies are still applied for safety.
            dietary_preferences=[],
            allergies=getattr(profile, "allergies", None) or [],
            cooking_equipment=cooking_equipment or [],
            cuisine_region=cuisine_region,
            protein_target=protein_target,
            carbs_target=carbs_target,
            fat_target=fat_target,
        )
        logger.info(f"Creating new session {session.id}")
        return session, []

    async def generate_discovery(
        self,
        user_id: str,
        meal_type: str,
        meal_portion_type: str,
        ingredients: List[str],
        cooking_time_minutes: Optional[int] = None,
        session_id: Optional[str] = None,
        language: str = "en",
        cuisine_region: Optional[str] = None,
        calorie_target_override: Optional[int] = None,
        protein_target: Optional[float] = None,
        carbs_target: Optional[float] = None,
        fat_target: Optional[float] = None,
        count: int = 6,
    ) -> Tuple[SuggestionSession, List[dict]]:
        """Lightweight discovery: names + macros only. No recipes."""
        is_existing = False
        if session_id:
            try:
                session, exclude_names = await self._load_existing_session(session_id, user_id, language)
                is_existing = True
            except ValueError:
                session, exclude_names = await self._create_new_session(
                    user_id, meal_type, meal_portion_type, ingredients, cooking_time_minutes,
                    language, 1, [], cuisine_region,
                    calorie_target_override, protein_target, carbs_target, fat_target,
                )
        else:
            session, exclude_names = await self._create_new_session(
                user_id, meal_type, meal_portion_type, ingredients, cooking_time_minutes,
                language, 1, [], cuisine_region,
                calorie_target_override, protein_target, carbs_target, fat_target,
            )

        meals = await self._recipe_generator.generate_discovery(
            session=session, exclude_meal_names=exclude_names, count=count,
        )

        # Track shown names for "load more" exclusion
        session.add_shown_meals([m["name"] for m in meals])
        if is_existing:
            await self._repo.update_session(session)
        else:
            await self._repo.save_session(session)

        return session, meals
