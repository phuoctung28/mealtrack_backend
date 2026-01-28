"""
Orchestration service for Phase 06 meal suggestions with full recipe support.
Handles session tracking, AI generation with timeout, and portion multipliers.
"""

import asyncio
import logging
import time
import uuid
from typing import List, Optional, Tuple, Callable, Any

from src.domain.cache.cache_keys import CacheKeys
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.meal_suggestion import (
    MealSuggestion,
    SuggestionSession,
    MacroEstimate,
    Ingredient,
    RecipeStep,
    MealType,
)
from src.domain.model.user import TdeeRequest, Sex, Goal, UnitSystem
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.ports.meal_suggestion_repository_port import (
    MealSuggestionRepositoryPort,
)
from src.domain.services.meal_suggestion.translation_service import TranslationService
from src.domain.services.portion_calculation_service import PortionCalculationService
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


class SuggestionOrchestrationService:
    """
    Orchestrates meal suggestion generation with session tracking.
    Implements timeout handling and portion multipliers.
    
    This service is designed to be used as a singleton in the event bus.
    It uses ScopedSession internally to get the current request's database session,
    ensuring proper isolation while allowing the service to be reused.
    """

    GENERATION_TIMEOUT_SECONDS = 35  # Reduced from 45s with optimized prompts
    SUGGESTIONS_COUNT = 3
    MIN_ACCEPTABLE_RESULTS = 2  # Return at least 2 meals for acceptable UX

    # Parallel generation constants (OPTIMIZED)
    PARALLEL_SINGLE_MEAL_TOKENS = 6000  # Increased for complete recipe JSON
    PARALLEL_SINGLE_MEAL_TIMEOUT = 25  # Increased to accommodate P95 latency (~22s + buffer)
    PARALLEL_STAGGER_MS = (
        200  # Reduced from 500ms (API handles smaller payloads faster)
    )

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        suggestion_repo: MealSuggestionRepositoryPort,
        tdee_service: TdeeCalculationService = None,
        portion_service: PortionCalculationService = None,
        redis_client=None,
        profile_provider: Optional[Callable[[str], Any]] = None,
    ):
        self._generation = generation_service
        self._repo = suggestion_repo
        self._tdee_service = tdee_service or TdeeCalculationService()
        self._portion_service = portion_service or PortionCalculationService()
        self._redis_client = redis_client
        self._translation_service = TranslationService(generation_service)
        # Profile provider is an application/infra concern injected from outside.
        # It should be a callable: user_id (str) -> user profile domain object.
        self._profile_provider = profile_provider

    async def generate_suggestions(
        self,
        user_id: str,
        meal_type: str,
        meal_portion_type: str,
        ingredients: List[str],
        cooking_time_minutes: int,
        session_id: Optional[str] = None,
        language: str = "en",
        servings: int = 1,
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """
        Generate 3 suggestions. If session_id provided, generates NEW meals
        excluding previously shown ones. Otherwise creates new session.
        """
        # Check if regenerating from existing session
        if session_id:
            session = await self._repo.get_session(session_id)
            if not session:
                # Session expired or not found - log warning and create new session
                logger.warning(
                    f"Session {session_id} not found or expired (TTL: 4h). "
                    f"Creating new session for user {user_id}"
                )
                session_id = None  # Force new session creation
            elif session.user_id != user_id:
                # Security check: session exists but belongs to different user
                logger.warning(
                    f"Session {session_id} exists but user_id mismatch: "
                    f"expected {user_id}, got {session.user_id}"
                )
                session_id = None  # Force new session creation for this user

            # Use existing session's shown meal names as exclusions
            exclude_meal_names = session.shown_meal_names
            logger.info(
                f"Regenerating for session {session_id}, "
                f"excluding {len(exclude_meal_names)} previous meals"
            )
        else:
            # Get user profile via injected provider (keeps domain decoupled from infra)
            if not self._profile_provider:
                raise RuntimeError("Profile provider is not configured for SuggestionOrchestrationService")

            profile = self._profile_provider(user_id)
            if not profile:
                raise ValueError(f"User {user_id} profile not found")

            # Use cached TDEE (changed from direct calculation)
            daily_tdee = await self._get_cached_tdee(user_id, profile)

            # Get meals_per_day from profile (default to 3)
            meals_per_day = getattr(profile, "meals_per_day", 3)

            # Calculate target calories using PortionCalculationService
            portion_target = self._portion_service.get_target_for_meal_type(
                meal_type=meal_portion_type,
                daily_target=int(daily_tdee),
                meals_per_day=meals_per_day,
            )
            # Multiply target calories by servings (1-4x)
            target_calories = portion_target.target_calories * servings

            # Extract dietary preferences and allergies (Phase 1 optimization)
            dietary_preferences = getattr(profile, "dietary_preferences", None) or []
            allergies = getattr(profile, "allergies", None) or []

            # Create new session with dietary info, language, and servings
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
                dietary_preferences=dietary_preferences,
                allergies=allergies,
            )
            exclude_meal_names = []
            logger.info(f"Creating new session {session.id}")

        # Generate with timeout, excluding previous meal names
        suggestions = await self._generate_with_timeout(
            session=session,
            exclude_meal_names=exclude_meal_names,
        )

        # Track shown IDs and meal names
        session.add_shown_ids([s.id for s in suggestions])
        session.add_shown_meals([s.meal_name for s in suggestions])

        # Persist session and suggestions using port-compliant methods
        if session_id:
            await self._repo.update_session(session)
        else:
            await self._repo.save_session(session)
        await self._repo.save_suggestions(suggestions)

        return session, suggestions

    def _calculate_daily_tdee(self, profile) -> float:
        """
        Calculate daily TDEE (Total Daily Energy Expenditure) from user profile.
        Returns target calories based on user's fitness goal.
        """
        try:
            # Map profile data to TDEE request using centralized mapper
            sex = Sex.MALE if profile.gender.lower() == "male" else Sex.FEMALE

            tdee_request = TdeeRequest(
                age=profile.age,
                sex=sex,
                height=profile.height_cm,
                weight=profile.weight_kg,
                activity_level=ActivityGoalMapper.map_activity_level(profile.activity_level),
                goal=ActivityGoalMapper.map_goal(profile.fitness_goal),
                body_fat_pct=profile.body_fat_percentage,
                unit_system=UnitSystem.METRIC,
            )

            # Calculate TDEE
            result = self._tdee_service.calculate_tdee(tdee_request)
            return result.macros.calories

        except Exception as e:
            logger.warning(
                f"Failed to calculate TDEE: {e}. Using default 2000 calories."
            )
            return 2000.0

    async def _get_cached_tdee(self, user_id: str, profile) -> float:
        """
        Get TDEE from cache or calculate and cache it.
        Uses 24h TTL since TDEE changes only when profile changes.
        """
        if not self._redis_client:
            # No cache available, calculate directly
            return self._calculate_daily_tdee(profile)

        cache_key, ttl = CacheKeys.user_tdee(user_id)

        try:
            cached = await self._redis_client.get(cache_key)
            if cached:
                logger.debug(f"TDEE cache HIT for user {user_id}")
                return float(cached)
        except Exception as e:
            logger.warning(f"TDEE cache GET failed: {e}")

        # Calculate and cache
        tdee = self._calculate_daily_tdee(profile)

        try:
            await self._redis_client.set(cache_key, str(tdee), ttl)
            logger.debug(f"TDEE cached for user {user_id}: {tdee}")
        except Exception as e:
            logger.warning(f"TDEE cache SET failed: {e}")

        return tdee

    async def _generate_with_timeout(
        self,
        session: SuggestionSession,
        exclude_meal_names: List[str],
    ) -> List[MealSuggestion]:
        """
        Generate suggestions using 2-phase approach.
        Phase 1: Generate 4 diverse meal names (~1s)
        Phase 2: Generate 4 recipes in parallel, take first 3 successful (~8-10s)
        Target latency: 9-12s (9-11s average, 12-14s P95)
        """
        return await self._generate_parallel_hybrid(session, exclude_meal_names)

    def _get_language_name(self, code: str) -> str:
        """Map language code to full English name for prompt instructions."""
        languages = {
            "en": "English",
            "vi": "Vietnamese",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ru": "Russian",
            "pt": "Portuguese",
            "hi": "Hindi",
            "ar": "Arabic",
            "tr": "Turkish",
            "nl": "Dutch",
            "pl": "Polish",
            "sv": "Swedish",
            "da": "Danish",
            "fi": "Finnish",
            "no": "Norwegian",
            "cs": "Czech",
            "el": "Greek",
            "he": "Hebrew",
            "id": "Indonesian",
            "ms": "Malay",
            "th": "Thai",
        }
        return languages.get(code.lower(), "English")

    async def _generate_parallel_hybrid(
        self,
        session: SuggestionSession,
        exclude_meal_names: List[str],
    ) -> List[MealSuggestion]:
        """
        Three-phase generation with over-generation for reliability.
        Phase 1: Generate 4 diverse meal names (1 call, ~1-2s)
        Phase 2: Generate 4 recipes in parallel, take first 3 successes (~6-8s)
        Phase 3: Translate to target language if non-English (~2-3s)
        Target latency: 9-13s (7-10s for English, 9-13s for non-English)

        Args:
            session: The suggestion session with user preferences
            exclude_meal_names: List of meal names to avoid (from previous generations)
        """
        start_time = time.time()
        target_lang = self._get_language_name(session.language)

        # STEP 1: Generate 4 diverse meal names in one call
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import (
            build_meal_names_prompt,
            build_recipe_details_prompt,
        )
        from src.domain.schemas.meal_generation_schemas import (
            MealNamesResponse,
            RecipeDetailsResponse,
        )

        logger.info(
            f"[PHASE-1-START] session={session.id} | "
            f"generating 4 diverse meal names in {target_lang} | "
            f"excluding {len(exclude_meal_names)} previous meals"
        )

        names_prompt = build_meal_names_prompt(session, exclude_meal_names)

        # Generate directly in target language
        names_system = (
            f"You are a creative chef. Generate 4 VERY DIFFERENT meal names with "
            f"diverse flavors and cooking styles. Output content in {target_lang}. "
            "IMPORTANT: Keep all JSON keys (like 'meal_names') in English."
        )

        phase1_elapsed = 0.0  # Initialize to prevent UnboundLocalError
        try:
            names_raw = await asyncio.wait_for(
                asyncio.to_thread(
                    self._generation.generate_meal_plan,
                    names_prompt,
                    names_system,
                    "json",
                    1000,  # Token limit for name generation
                    MealNamesResponse,  # Structured output schema (guarantees valid format)
                    "meal_names",  # Use high-RPM model (gemini-2.5-flash-lite, 10 RPM)
                ),
                timeout=20,  # Increased timeout to accommodate AI response time
            )

            meal_names = names_raw.get("meal_names", [])

            # Deduplicate meal names while preserving order
            seen = set()
            unique_names = []
            for name in meal_names:
                if name.lower() not in seen:
                    seen.add(name.lower())
                    unique_names.append(name)
            meal_names = unique_names

            if len(meal_names) < self.SUGGESTIONS_COUNT:
                logger.warning(
                    f"[PHASE-1-INCOMPLETE] session={session.id} | "
                    f"got {len(meal_names)} names, expected {self.SUGGESTIONS_COUNT}"
                )
                raise RuntimeError("Could not generate enough unique meal names.")

            phase1_elapsed = time.time() - start_time
            logger.info(
                f"[PHASE-1-COMPLETE] session={session.id} | "
                f"elapsed={phase1_elapsed:.2f}s | "
                f"names={meal_names}"
            )

        except Exception as e:
            phase1_elapsed = time.time() - start_time
            logger.error(
                f"[PHASE-1-FAILED] session={session.id} | "
                f"elapsed={phase1_elapsed:.2f}s | "
                f"error_type={type(e).__name__} | error={e}"
            )
            raise RuntimeError(f"Failed to generate meal names: {e}") from e

        # STEP 2: Generate full recipes for each name in parallel
        logger.info(
            f"[PHASE-2-START] session={session.id} | generating recipes for {meal_names}"
        )

        recipe_prompts = [
            build_recipe_details_prompt(meal_name, session) for meal_name in meal_names
        ]

        # Generate details directly in target language
        recipe_system = (
            f"You are a professional chef. Generate complete recipe details as valid JSON. "
            f"CRITICAL: MUST finish entire JSON. Output string values in {target_lang}. "
            "JSON KEYS (e.g., 'ingredients', 'recipe_steps', 'amount', 'unit') MUST BE IN ENGLISH."
        )

        def get_alternate_purpose(purpose: str) -> str:
            """Get alternate model purpose for retry on failure."""
            if purpose == "recipe_primary":
                return "recipe_secondary"
            elif purpose == "recipe_secondary":
                return "recipe_primary"
            return purpose  # No alternate for meal_names

        async def attempt_generation(
            prompt: str,
            meal_name: str,
            index: int,
            model_purpose: str,
            is_retry: bool = False,
        ) -> Optional[MealSuggestion]:
            """Single generation attempt with specified model purpose."""
            retry_marker = "[RETRY]" if is_retry else ""

            try:
                raw = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._generation.generate_meal_plan,
                        prompt,
                        recipe_system,
                        "json",
                        self.PARALLEL_SINGLE_MEAL_TOKENS,
                        RecipeDetailsResponse,
                        model_purpose,
                    ),
                    timeout=self.PARALLEL_SINGLE_MEAL_TIMEOUT,
                )

                # Parse recipe response (guaranteed valid by Pydantic schema)
                recipe_data = raw

                ingredients = recipe_data.get("ingredients", [])
                recipe_steps = recipe_data.get("recipe_steps", [])
                prep_time = recipe_data.get(
                    "prep_time_minutes", session.cooking_time_minutes
                )

                if not ingredients or not recipe_steps:
                    logger.warning(
                        f"[PHASE-2-UNEXPECTED-EMPTY]{retry_marker} index={index} | "
                        f"ingredients={len(ingredients)} | steps={len(recipe_steps)}"
                    )
                    return None

                calories = recipe_data.get("calories", session.target_calories)
                protein = recipe_data.get("protein", 20.0)
                carbs = recipe_data.get("carbs", 30.0)
                fat = recipe_data.get("fat", 10.0)

                logger.info(
                    f"[PHASE-2-SUCCESS]{retry_marker} index={index} | "
                    f"model_purpose={model_purpose} | meal_name={meal_name}"
                )

                return MealSuggestion(
                    id=f"sug_{uuid.uuid4().hex[:16]}",
                    session_id=session.id,
                    user_id=session.user_id,
                    meal_name=meal_name,
                    description="",
                    meal_type=MealType(session.meal_type),
                    macros=MacroEstimate(
                        calories=calories,
                        protein=protein,
                        carbs=carbs,
                        fat=fat,
                    ),
                    ingredients=[Ingredient(**ing) for ing in ingredients],
                    recipe_steps=[RecipeStep(**step) for step in recipe_steps],
                    prep_time_minutes=prep_time,
                    confidence_score=0.85,
                )

            except asyncio.TimeoutError:
                logger.warning(
                    f"[PHASE-2-TIMEOUT]{retry_marker} index={index} | "
                    f"model_purpose={model_purpose} | meal_name={meal_name}"
                )
                return None
            except Exception as e:
                logger.warning(
                    f"[PHASE-2-FAIL]{retry_marker} index={index} | "
                    f"model_purpose={model_purpose} | error_type={type(e).__name__} | error={e}"
                )
                return None

        async def generate_recipe(
            prompt: str, meal_name: str, index: int
        ) -> Optional[MealSuggestion]:
            """Generate recipe with retry on alternate model if first attempt fails."""
            # Alternate between primary (even) and secondary (odd) for first attempt
            model_purpose = "recipe_primary" if index % 2 == 0 else "recipe_secondary"

            # First attempt
            result = await attempt_generation(
                prompt, meal_name, index, model_purpose, is_retry=False
            )

            if result is not None:
                return result

            # Retry with alternate model (uses different rate limit pool)
            alternate_purpose = get_alternate_purpose(model_purpose)
            logger.info(
                f"[PHASE-2-RETRY] index={index} | "
                f"original={model_purpose} | fallback={alternate_purpose} | "
                f"meal_name={meal_name}"
            )

            return await attempt_generation(
                prompt, meal_name, index, alternate_purpose, is_retry=True
            )

        # Over-generation strategy: Start 4 recipes, take first 3 successes
        # Removed stagger to maximize speed
        gen_start = time.time()

        # Create tasks simultaneously
        tasks = []
        for i in range(4):
            # No delay/stagger
            task = asyncio.create_task(
                generate_recipe(recipe_prompts[i], meal_names[i], i)
            )
            tasks.append(task)

        # Use as_completed to get first 3 successes and cancel remaining
        successful_results = []
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result is not None:
                    successful_results.append(result)
                    logger.debug(f"[SUCCESS] Got meal {len(successful_results)}/3")
                    if len(successful_results) >= 3:
                        # Cancel remaining tasks immediately
                        cancelled_count = sum(
                            1
                            for task in tasks
                            if not task.done() and not task.cancel() is False
                        )
                        logger.info(
                            f"[EARLY-STOP] Got 3 meals, cancelled {cancelled_count} remaining tasks"
                        )
                        break
            except Exception as e:
                logger.warning(f"[RECIPE-ERROR] {type(e).__name__}: {e}")
                continue

        phase2_elapsed = time.time() - gen_start
        logger.info(
            f"[PHASE-2-COMPLETE] session={session.id} | "
            f"success={len(successful_results)}/4 | "
            f"gen_elapsed={phase2_elapsed:.2f}s"
        )

        # Check for minimum acceptable results
        if len(successful_results) < self.MIN_ACCEPTABLE_RESULTS:
            if not successful_results:
                raise RuntimeError("Failed to generate any recipes from 4 attempts")
            else:
                logger.error(
                    f"[PHASE-2-INSUFFICIENT] session={session.id} | "
                    f"only {len(successful_results)} meals (minimum {self.MIN_ACCEPTABLE_RESULTS} required)"
                )
                raise RuntimeError(
                    f"Insufficient recipes generated: {len(successful_results)}/{self.MIN_ACCEPTABLE_RESULTS} minimum"
                )

        # Log if partial success but acceptable
        if len(successful_results) < 3:
            logger.warning(
                f"[PHASE-2-PARTIAL] session={session.id} | "
                f"returning {len(successful_results)}/3 meals (above minimum threshold)"
            )

        suggestions = successful_results

        # PHASE 3: Translate if non-English language
        phase3_elapsed = 0.0
        if session.language and session.language != "en":
            phase3_start = time.time()
            lang_name = target_lang
            logger.info(
                f"[PHASE-3-START] session={session.id} | "
                f"translating {len(suggestions)} meals to {lang_name}"
            )

            try:
                suggestions = (
                    await self._translation_service.translate_meal_suggestions_batch(
                        suggestions, session.language
                    )
                )
                phase3_elapsed = time.time() - phase3_start
                logger.info(
                    f"[PHASE-3-COMPLETE] session={session.id} | "
                    f"elapsed={phase3_elapsed:.2f}s | "
                    f"translated={len(suggestions)} meals to {lang_name}"
                )
            except Exception as e:
                phase3_elapsed = time.time() - phase3_start
                logger.error(
                    f"[PHASE-3-FAILED] session={session.id} | "
                    f"elapsed={phase3_elapsed:.2f}s | "
                    f"error={type(e).__name__}: {e} | "
                    f"returning English suggestions as fallback"
                )

        total_elapsed = time.time() - start_time

        logger.info(
            f"[PIPELINE-COMPLETE] session={session.id} | "
            f"total_elapsed={total_elapsed:.2f}s | "
            f"phase1={phase1_elapsed:.2f}s | "
            f"phase2={phase2_elapsed:.2f}s | "
            f"phase3={phase3_elapsed:.2f}s | "
            f"language={session.language} | "
            f"returned={len(suggestions)} meals (target 3) | "
            f"meals={[s.meal_name for s in suggestions]}"
        )

        return suggestions
