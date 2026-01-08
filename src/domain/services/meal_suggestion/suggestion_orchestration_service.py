"""
Orchestration service for Phase 06 meal suggestions with full recipe support.
Handles session tracking, AI generation with timeout, and portion multipliers.
"""


import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from src.domain.model.meal_suggestion import (
    MealSuggestion,
    SuggestionSession,
    SuggestionStatus,
    MacroEstimate,
    Ingredient,
    RecipeStep,
    MealType,
)
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.ports.meal_suggestion_repository_port import (
    MealSuggestionRepositoryPort,
)
from src.domain.ports.user_repository_port import UserRepositoryPort
from src.domain.services.portion_calculation_service import PortionCalculationService
from src.domain.services.tdee_service import TdeeCalculationService

from src.domain.services.meal_suggestion.recipe_search_service import RecipeSearchService, RecipeSearchCriteria
from src.domain.model.user import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem
from src.domain.cache.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class SuggestionOrchestrationService:
    """
    Orchestrates meal suggestion generation with session tracking.
    Implements timeout handling and portion multipliers.
    """

    GENERATION_TIMEOUT_SECONDS = 35  # Reduced from 45s with optimized prompts
    SUGGESTIONS_COUNT = 3
    MIN_ACCEPTABLE_RESULTS = 2  # Return at least 2 meals for acceptable UX

    # Parallel generation constants (OPTIMIZED)
    PARALLEL_SINGLE_MEAL_TOKENS = 4000  # Reduced from 4000 with compressed prompts
    PARALLEL_SINGLE_MEAL_TIMEOUT = 20   # Reduced from 25s (faster with smaller prompts)
    PARALLEL_STAGGER_MS = 200  # Reduced from 500ms (API handles smaller payloads faster)

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        suggestion_repo: MealSuggestionRepositoryPort,
        user_repo: UserRepositoryPort,
        tdee_service: TdeeCalculationService = None,
        portion_service: PortionCalculationService = None,
        recipe_search: RecipeSearchService = None,
        redis_client=None,
    ):
        self._generation = generation_service
        self._repo = suggestion_repo
        self._user_repo = user_repo
        self._tdee_service = tdee_service or TdeeCalculationService()
        self._portion_service = portion_service or PortionCalculationService()
        self._recipe_search = recipe_search  # Optional for Phase 2
        self._redis_client = redis_client

    async def generate_suggestions(
        self,
        user_id: str,
        meal_type: str,
        meal_portion_type: str,
        ingredients: List[str],
        cooking_time_minutes: int,
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """Generate initial 3 suggestions and create session."""
        # Get user profile using port-compliant method
        profile = await asyncio.to_thread(self._user_repo.get_profile, user_id)
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
        target_calories = portion_target.target_calories

        # Extract dietary preferences and allergies (Phase 1 optimization)
        dietary_preferences = getattr(profile, 'dietary_preferences', None) or []
        allergies = getattr(profile, 'allergies', None) or []

        # Create session with dietary info
        session = SuggestionSession(
            id=f"session_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            meal_type=meal_type,
            meal_portion_type=meal_portion_type,
            target_calories=target_calories,
            ingredients=ingredients,
            cooking_time_minutes=cooking_time_minutes,
            dietary_preferences=dietary_preferences,
            allergies=allergies,
        )

        # Generate with timeout
        suggestions = await self._generate_with_timeout(
            session=session,
            exclude_ids=[],
        )

        # Track shown IDs
        session.add_shown_ids([s.id for s in suggestions])

        # Persist session and suggestions using port-compliant methods
        await self._repo.save_session(session)
        await self._repo.save_suggestions(suggestions)

        return session, suggestions

    async def regenerate_suggestions(
        self,
        user_id: str,
        session_id: str,
        exclude_ids: List[str],
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """Regenerate 3 NEW suggestions excluding previously shown."""
        session = await self._repo.get_session(session_id)
        if not session or session.user_id != user_id:
            raise ValueError(f"Session {session_id} not found")

        # Combine shown with explicitly excluded
        all_excluded = list(set(session.shown_suggestion_ids + exclude_ids))

        # Generate new suggestions
        suggestions = await self._generate_with_timeout(
            session=session,
            exclude_ids=all_excluded,
        )

        # Update session
        session.add_shown_ids([s.id for s in suggestions])
        await self._repo.update_session(session)
        await self._repo.save_suggestions(suggestions)

        return session, suggestions

    async def get_session_suggestions(
        self,
        user_id: str,
        session_id: str,
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """Get current session suggestions."""
        session = await self._repo.get_session(session_id)
        if not session or session.user_id != user_id:
            raise ValueError(f"Session {session_id} not found")

        suggestions = await self._repo.get_session_suggestions(session_id)
        return session, suggestions

    async def accept_suggestion(
        self,
        user_id: str,
        suggestion_id: str,
        portion_multiplier: int,
        consumed_at: Optional[datetime],
    ) -> dict:
        """Accept suggestion with portion multiplier (returns meal data for saving)."""
        suggestion = await self._repo.get_suggestion(suggestion_id)
        if not suggestion or suggestion.user_id != user_id:
            raise ValueError(f"Suggestion {suggestion_id} not found")

        # Apply portion multiplier
        adjusted_macros = suggestion.macros.multiply(portion_multiplier)

        # Mark as accepted
        suggestion.status = SuggestionStatus.ACCEPTED
        await self._repo.update_suggestion(suggestion)

        return {
            "meal_id": f"meal_{uuid.uuid4().hex[:16]}",
            "meal_name": suggestion.meal_name,
            "adjusted_macros": adjusted_macros,
            "saved_at": consumed_at or datetime.utcnow(),
            "suggestion": suggestion,
        }

    async def reject_suggestion(
        self,
        user_id: str,
        suggestion_id: str,
        feedback: Optional[str],
    ) -> None:
        """Reject suggestion with optional feedback."""
        suggestion = await self._repo.get_suggestion(suggestion_id)
        if not suggestion or suggestion.user_id != user_id:
            raise ValueError(f"Suggestion {suggestion_id} not found")

        suggestion.status = SuggestionStatus.REJECTED
        await self._repo.update_suggestion(suggestion)
        logger.info(f"Rejected suggestion {suggestion_id}: {feedback}")

    async def discard_session(
        self,
        user_id: str,
        session_id: str,
    ) -> None:
        """Discard entire session and cleanup."""
        session = await self._repo.get_session(session_id)
        if not session or session.user_id != user_id:
            raise ValueError(f"Session {session_id} not found")

        await self._repo.delete_session(session_id)

    def _calculate_daily_tdee(self, profile) -> float:
        """
        Calculate daily TDEE (Total Daily Energy Expenditure) from user profile.
        Returns target calories based on user's fitness goal.
        """
        try:
            # Map profile data to TDEE request
            sex = Sex.MALE if profile.gender.lower() == "male" else Sex.FEMALE

            activity_map = {
                "sedentary": ActivityLevel.SEDENTARY,
                "light": ActivityLevel.LIGHT,
                "moderate": ActivityLevel.MODERATE,
                "active": ActivityLevel.ACTIVE,
                "extra": ActivityLevel.EXTRA,
                "extra": ActivityLevel.EXTRA,
            }

            goal_map = {
                "cut": Goal.CUT,
                "bulk": Goal.BULK,
                "recomp": Goal.RECOMP,
            }

            tdee_request = TdeeRequest(
                age=profile.age,
                sex=sex,
                height=profile.height_cm,
                weight=profile.weight_kg,
                activity_level=activity_map.get(
                    profile.activity_level, ActivityLevel.MODERATE
                ),
                goal=goal_map.get(profile.fitness_goal, Goal.RECOMP),
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
        exclude_ids: List[str],
    ) -> List[MealSuggestion]:
        """
        Generate suggestions using 2-phase approach.
        Phase 1: Generate 6 diverse meal names (~1s)
        Phase 2: Generate 6 recipes in parallel, take first 3 successful (~8-10s)
        Target latency: 9-12s (9-11s average, 12-14s P95)
        """
        return await self._generate_parallel_hybrid(session, exclude_ids)

    async def _generate_parallel_hybrid(
        self,
        session: SuggestionSession,
        exclude_ids: List[str],
    ) -> List[MealSuggestion]:
        """
        Two-phase generation with over-generation for reliability.
        Phase 1: Generate 4 diverse meal names (1 call, ~1-2s)
        Phase 2: Generate 4 recipes in parallel, take first 3 successes (~6-8s)
        Target latency: 7-10s (faster + more reliable with reduced API pressure)
        """
        start_time = time.time()

        # STEP 1: Generate 4 diverse meal names in one call
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import (
            build_meal_names_prompt,
            build_recipe_details_prompt,
        )
        from src.domain.schemas.meal_generation_schemas import (
            MealNamesResponse,
            RecipeDetailsResponse,
        )

        logger.info(f"[PHASE-1-START] session={session.id} | generating 4 diverse meal names")

        names_prompt = build_meal_names_prompt(session)
        names_system = "You are a creative chef. Generate 4 VERY DIFFERENT meal names with diverse flavors and cooking styles."
        
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
                ),
                timeout=10,  # Quick timeout for name generation
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

            if len(meal_names) != 4:
                logger.warning(
                    f"[PHASE-1-INCOMPLETE] session={session.id} | "
                    f"got {len(meal_names)} names, expected 4"
                )
                # Pad with generic names if needed
                while len(meal_names) < 4:
                    meal_names.append(f"Healthy {session.meal_type.title()} #{len(meal_names) + 1}")
            
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
            # Fallback to generic names
            meal_names = [
                f"Healthy {session.meal_type.title()} #{i+1}"
                for i in range(4)
            ]
        
        # STEP 2: Generate full recipes for each name in parallel
        logger.info(f"[PHASE-2-START] session={session.id} | generating recipes for {meal_names}")
        
        recipe_prompts = [
            build_recipe_details_prompt(meal_name, session)
            for meal_name in meal_names
        ]
        
        # Generate recipes in parallel
        recipe_system = "You are a professional chef. Generate complete recipe details as valid JSON. CRITICAL: MUST finish entire JSON - include all fields."

        async def generate_recipe(prompt: str, meal_name: str, index: int) -> Optional[MealSuggestion]:
            """Generate recipe details for a given meal name."""
            try:
                raw = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._generation.generate_meal_plan,
                        prompt,
                        recipe_system,
                        "json",
                        self.PARALLEL_SINGLE_MEAL_TOKENS,
                        RecipeDetailsResponse,  # Structured output schema
                    ),
                    timeout=self.PARALLEL_SINGLE_MEAL_TIMEOUT,
                )

                # Parse recipe response (guaranteed valid by Pydantic schema)
                recipe_data = raw
                
                # Extract validated fields (schema ensures these exist and are valid)
                # NOTE: description field removed in Phase 01 schema optimization
                ingredients = recipe_data.get("ingredients", [])
                recipe_steps = recipe_data.get("recipe_steps", [])
                prep_time = recipe_data.get("prep_time_minutes", session.cooking_time_minutes)
                
                # Schema guarantees 4-6 ingredients and 3-4 steps, but double-check
                if not ingredients or not recipe_steps:
                    logger.warning(
                        f"[PHASE-2-UNEXPECTED-EMPTY] index={index} | "
                        f"ingredients={len(ingredients)} | steps={len(recipe_steps)}"
                    )
                    return None
                
                # Build MealSuggestion with the meal_name from Phase 1
                return MealSuggestion(
                    id=f"sug_{uuid.uuid4().hex[:16]}",
                    session_id=session.id,
                    user_id=session.user_id,
                    meal_name=meal_name,  # Use name from Phase 1
                    description="",  # Empty string (field removed from schema in Phase 01)
                    meal_type=MealType(session.meal_type),
                    macros=MacroEstimate(
                        calories=session.target_calories,
                        protein=20,
                        carbs=30,
                        fat=10,  # Placeholder, will be enriched
                    ),
                    ingredients=[Ingredient(**ing) for ing in ingredients],
                    recipe_steps=[RecipeStep(**step) for step in recipe_steps],
                    prep_time_minutes=prep_time,
                    confidence_score=0.85,
                )
            
            except asyncio.TimeoutError:
                logger.warning(
                    f"[PHASE-2-TIMEOUT] index={index} | "
                    f"meal_name={meal_name} | timeout={self.PARALLEL_SINGLE_MEAL_TIMEOUT}s"
                )
                return None
            except Exception as e:
                logger.warning(
                    f"[PHASE-2-FAIL] index={index} | "
                    f"meal_name={meal_name} | error_type={type(e).__name__} | error={e}"
                )
                return None

        # Over-generation strategy: Start 4 recipes, take first 3 successes
        # Staggered starts (500ms) to prevent rate limiting
        gen_start = time.time()

        # Create tasks with staggered starts
        tasks = []
        for i in range(4):
            if i > 0:
                # Add 500ms delay to prevent rate limiting (reduced from 6 to 4 parallel)
                await asyncio.sleep(self.PARALLEL_STAGGER_MS / 1000)
                logger.debug(f"[STAGGER] Starting request {i} after {self.PARALLEL_STAGGER_MS}ms delay")

            task = asyncio.create_task(
                generate_recipe(recipe_prompts[i], meal_names[i], i)
            )
            tasks.append(task)

        # Use as_completed to get first 3 successes and cancel remaining (S1 fix: cancel inside loop)
        successful_results = []
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result is not None:
                    successful_results.append(result)
                    logger.debug(f"[SUCCESS] Got meal {len(successful_results)}/3")
                    if len(successful_results) >= 3:
                        # Cancel remaining tasks immediately (S1: cleaner pattern)
                        cancelled_count = sum(1 for task in tasks if not task.done() and not task.cancel() is False)
                        logger.info(f"[EARLY-STOP] Got 3 meals, cancelled {cancelled_count} remaining tasks")
                        break
            except Exception as e:
                logger.warning(f"[RECIPE-ERROR] {type(e).__name__}: {e}")
                continue

        logger.info(
            f"[PHASE-2-COMPLETE] session={session.id} | "
            f"success={len(successful_results)}/4 | "
            f"gen_elapsed={time.time() - gen_start:.2f}s"
        )

        # W2 fix: Check for minimum acceptable results
        if len(successful_results) < self.MIN_ACCEPTABLE_RESULTS:
            if not successful_results:
                raise RuntimeError(
                    f"Failed to generate any recipes from 4 attempts"
                )
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

        total_elapsed = time.time() - start_time
        phase2_elapsed = total_elapsed - phase1_elapsed
        
        logger.info(
            f"[TWO-PHASE-COMPLETE] session={session.id} | "
            f"total_elapsed={total_elapsed:.2f}s | "
            f"phase1={phase1_elapsed:.2f}s | "
            f"phase2={phase2_elapsed:.2f}s | "
            f"returned={len(suggestions)} meals (target 3) | "
            f"meals={[s.meal_name for s in suggestions]}"
        )

        return suggestions

    def _normalize_confidence(self, score: float) -> float:
        """Normalize confidence score to 0-1 range (AI may return 1-5 scale)."""
        if score > 1.0:
            # Assume 1-5 scale, convert to 0-1
            return min(1.0, score / 5.0)
        return max(0.0, min(1.0, score))
