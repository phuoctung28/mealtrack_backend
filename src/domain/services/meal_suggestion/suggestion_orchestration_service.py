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

logger = logging.getLogger(__name__)


class SuggestionOrchestrationService:
    """
    Orchestrates meal suggestion generation with session tracking.
    Implements timeout handling and portion multipliers.
    """

    GENERATION_TIMEOUT_SECONDS = 45  # Increased from 30s - full recipe generation needs ~30-35s
    SUGGESTIONS_COUNT = 3

    # Parallel generation constants
    PARALLEL_SINGLE_MEAL_TOKENS = 4000  # Token limit for complete JSON generation
    PARALLEL_SINGLE_MEAL_TIMEOUT = 25  # Per-request timeout

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

        # Calculate daily TDEE from profile
        daily_tdee = self._calculate_daily_tdee(profile)

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

    async def _generate_with_timeout(
        self,
        session: SuggestionSession,
        exclude_ids: List[str],
    ) -> List[MealSuggestion]:
        """
        Generate suggestions using parallel hybrid approach.
        Target latency: 8-10s (max 12s).

        Uses Pinecone for inspiration + 3 parallel AI calls for customization.
        """
        # Use parallel hybrid generation for faster, more accurate results
        return await self._generate_parallel_hybrid(session, exclude_ids)

    def _build_prompt(self, session: SuggestionSession, exclude_ids: List[str]) -> str:
        """Build compact AI prompt - ingredients only, NO macros."""
        # Limit ingredients to 10 for prompt efficiency
        ingredients_str = (
            ", ".join(session.ingredients[:10])
            if session.ingredients
            else "any common ingredients"
        )

        # Add dietary constraints if present
        constraints = []
        if hasattr(session, 'dietary_preferences') and session.dietary_preferences:
            constraints.append(f"Dietary: {', '.join(session.dietary_preferences)}")
        if hasattr(session, 'allergies') and session.allergies:
            constraints.append(f"Avoid: {', '.join(session.allergies)}")

        constraints_str = "\n" + "; ".join(constraints) if constraints else ""

        exclude_note = f"\nExclude {len(exclude_ids)} previous meals" if exclude_ids else ""

        return f"""Generate 3 {session.meal_type} meals (~{session.target_calories} cal, ≤{session.cooking_time_minutes}min).

Ingredients: {ingredients_str}{constraints_str}{exclude_note}

JSON (NO macros - backend calculates):
{{
  "suggestions": [
    {{
      "name": "Meal Name",
      "description": "Brief description",
      "ingredients": [{{"name": "chicken", "amount": 200, "unit": "g"}}],
      "recipe_steps": [{{"step": 1, "instruction": "Heat pan", "duration_minutes": 3}}],
      "prep_time_minutes": 15
    }}
  ]
}}

Rules: 3 meals, specific portions (e.g., "200g chicken"), 4-6 steps, NO calories/protein/carbs/fat."""

    def _parse_ai_response(
        self, raw_response: dict, session: SuggestionSession
    ) -> List[MealSuggestion]:
        """Parse AI JSON response into domain objects."""
        suggestions = []
        raw_suggestions = raw_response.get("suggestions", [])

        logger.debug(
            f"[MEAL-PARSE-START] session={session.id} | "
            f"raw_suggestions_count={len(raw_suggestions)} | "
            f"response_type={type(raw_response).__name__}"
        )

        for idx, raw in enumerate(raw_suggestions):
            try:
                # Log what we're trying to parse
                logger.debug(
                    f"[MEAL-PARSE-ITEM] session={session.id} | "
                    f"index={idx} | "
                    f"name={raw.get('name', 'N/A')[:30]} | "
                    f"has_macros={bool(raw.get('macros'))} | "
                    f"ingredients_count={len(raw.get('ingredients', []))} | "
                    f"steps_count={len(raw.get('recipe_steps', []))}"
                )

                suggestions.append(
                    MealSuggestion(
                        id=f"sug_{uuid.uuid4().hex[:16]}",
                        session_id=session.id,
                        user_id=session.user_id,
                        meal_name=raw.get("name", "Unnamed Meal"),
                        description=raw.get("description", ""),
                        meal_type=MealType(session.meal_type),
                        macros=MacroEstimate(
                            calories=raw.get("macros", {}).get(
                                "calories", session.target_calories
                            ),
                            protein=raw.get("macros", {}).get("protein", 20),
                            carbs=raw.get("macros", {}).get("carbs", 30),
                            fat=raw.get("macros", {}).get("fat", 10),
                        ),
                        ingredients=[
                            Ingredient(**ing) for ing in raw.get("ingredients", [])
                        ],
                        recipe_steps=[
                            RecipeStep(**step) for step in raw.get("recipe_steps", [])
                        ],
                        prep_time_minutes=raw.get(
                            "prep_time_minutes", session.cooking_time_minutes
                        ),
                        confidence_score=self._normalize_confidence(
                            raw.get("confidence_score", 0.85)
                        ),
                    )
                )
            except Exception as e:
                # Log detailed parsing failure
                raw_preview = str(raw)[:300] if raw else "None"
                logger.warning(
                    f"[MEAL-PARSE-FAIL] session={session.id} | "
                    f"index={idx} | "
                    f"error_type={type(e).__name__} | "
                    f"error={str(e)[:100]} | "
                    f"raw_preview={raw_preview}"
                )
                continue

        logger.debug(
            f"[MEAL-PARSE-COMPLETE] session={session.id} | "
            f"parsed={len(suggestions)}/{len(raw_suggestions)}"
        )
        return suggestions

    async def _generate_parallel_hybrid(
        self,
        session: SuggestionSession,
        exclude_ids: List[str],
    ) -> List[MealSuggestion]:
        """
        Two-phase generation for better variety and efficiency.
        Phase 1: Generate 3 diverse meal names (1 call, ~3-5s)
        Phase 2: Generate recipes in parallel (3 calls, ~10-15s)
        Target latency: 13-20s (better variety than single-phase)
        """
        start_time = time.time()

        # STEP 1: Generate 3 diverse meal names in one call
        from src.domain.services.meal_suggestion.suggestion_prompt_builder import (
            build_meal_names_prompt,
            build_recipe_details_prompt,
        )
        from src.domain.schemas.meal_generation_schemas import (
            MealNamesResponse,
            RecipeDetailsResponse,
        )

        logger.info(f"[PHASE-1-START] session={session.id} | generating 3 diverse meal names")
        
        names_prompt = build_meal_names_prompt(session)
        names_system = "You are a creative chef. Generate 3 VERY DIFFERENT meal names with diverse flavors and cooking styles."
        
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
            
            if len(meal_names) != 3:
                logger.warning(
                    f"[PHASE-1-INCOMPLETE] session={session.id} | "
                    f"got {len(meal_names)} names, expected 3"
                )
                # Pad with generic names if needed
                while len(meal_names) < 3:
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
                for i in range(3)
            ]
        
        # STEP 2: Generate full recipes for each name in parallel
        logger.info(f"[PHASE-2-START] session={session.id} | generating recipes for {meal_names}")
        
        recipe_prompts = [
            build_recipe_details_prompt(meal_name, session)
            for meal_name in meal_names
        ]
        
        # Generate recipes in parallel with retry logic
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
                        4000,  # Token limit for recipe generation
                        RecipeDetailsResponse,  # Structured output schema (guarantees valid format)
                    ),
                    timeout=self.PARALLEL_SINGLE_MEAL_TIMEOUT,
                )

                # Parse recipe response (guaranteed valid by Pydantic schema)
                recipe_data = raw
                
                # Extract validated fields (schema ensures these exist and are valid)
                description = recipe_data.get("description", "")
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
                    description=description,
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

        # Initial generation - all 3 recipes in parallel
        gen_start = time.time()
        results: List[Optional[MealSuggestion]] = list(await asyncio.gather(
            generate_recipe(recipe_prompts[0], meal_names[0], 0),
            generate_recipe(recipe_prompts[1], meal_names[1], 1),
            generate_recipe(recipe_prompts[2], meal_names[2], 2),
            return_exceptions=False,
        ))

        # C2 FIX: No retry logic - return results immediately
        successful_results = [r for r in results if r is not None]
        
        logger.info(
            f"[PHASE-2-COMPLETE] session={session.id} | "
            f"success={len(successful_results)}/3 | "
            f"gen_elapsed={time.time() - gen_start:.2f}s"
        )

        # STEP 3: Return partial or complete results
        failed_indices = [i for i, r in enumerate(results) if r is None]
        
        if failed_indices:
            failed_names = [meal_names[i] for i in failed_indices]
            logger.warning(
                f"[PHASE-2-PARTIAL-SUCCESS] session={session.id} | "
                f"success={len(successful_results)}/3 | "
                f"failed={len(failed_indices)} | "
                f"failed_meals={failed_names}"
            )
            
            # A3 FIX: If we have at least 1 successful meal, return it
            # Otherwise, raise error
            if not successful_results:
                raise RuntimeError(
                    f"Failed to generate any recipes after {self.PARALLEL_MAX_RETRIES} retries. "
                    f"All 3 meals failed: {failed_names}"
                )
        
        # Use successful results as-is (macros are placeholder estimates)
        suggestions = successful_results

        total_elapsed = time.time() - start_time
        phase2_elapsed = total_elapsed - phase1_elapsed
        
        logger.info(
            f"[TWO-PHASE-COMPLETE] session={session.id} | "
            f"total_elapsed={total_elapsed:.2f}s | "
            f"phase1={phase1_elapsed:.2f}s | "
            f"phase2={phase2_elapsed:.2f}s | "
            f"returned={len(suggestions)}/3 meals | "
            f"meals={[s.meal_name for s in suggestions]}"
        )

        return suggestions

    def _parse_single_meal(
        self,
        meal_data: dict,
        session: SuggestionSession,
        index: int,
    ) -> Optional[MealSuggestion]:
        """
        Parse single meal JSON into MealSuggestion.
        Returns None if response is incomplete (missing ingredients/steps).
        """
        # Validate required fields
        ingredients = meal_data.get("ingredients", [])
        recipe_steps = meal_data.get("recipe_steps", [])

        if not ingredients or len(ingredients) < 2:
            logger.warning(
                f"[PARSE-INVALID] index={index} | reason=missing_ingredients | "
                f"count={len(ingredients)}"
            )
            return None

        if not recipe_steps or len(recipe_steps) < 2:
            logger.warning(
                f"[PARSE-INVALID] index={index} | reason=missing_recipe_steps | "
                f"count={len(recipe_steps)}"
            )
            return None

        return MealSuggestion(
            id=f"sug_{uuid.uuid4().hex[:16]}",
            session_id=session.id,
            user_id=session.user_id,
            meal_name=meal_data.get("name", f"Meal {index + 1}"),
            description=meal_data.get("description", ""),
            meal_type=MealType(session.meal_type),
            macros=MacroEstimate(
                calories=session.target_calories,
                protein=20,
                carbs=30,
                fat=10,  # Placeholder - estimated values
            ),
            ingredients=[Ingredient(**ing) for ing in ingredients],
            recipe_steps=[RecipeStep(**step) for step in recipe_steps],
            prep_time_minutes=meal_data.get("prep_time_minutes", 20),
            confidence_score=0.85,
        )

    def _recipe_to_suggestion(
        self,
        recipe,
        session: SuggestionSession
    ) -> MealSuggestion:
        """Convert Pinecone recipe to MealSuggestion."""
        return MealSuggestion(
            id=f"sug_{uuid.uuid4().hex[:16]}",
            session_id=session.id,
            user_id=session.user_id,
            meal_name=recipe.name,
            description=recipe.description,
            meal_type=MealType(session.meal_type),
            macros=MacroEstimate(
                calories=recipe.macros['calories'],
                protein=recipe.macros['protein'],
                carbs=recipe.macros['carbs'],
                fat=recipe.macros['fat']
            ),
            ingredients=[
                Ingredient(
                    name=ing['name'],
                    amount=ing['amount'],
                    unit=ing['unit']
                )
                for ing in recipe.ingredients
            ],
            recipe_steps=[
                RecipeStep(
                    step=step['step'],
                    instruction=step['instruction'],
                    duration_minutes=step.get('duration_minutes')
                )
                for step in recipe.recipe_steps
            ],
            prep_time_minutes=recipe.prep_time_minutes,
            confidence_score=recipe.confidence_score,
        )

    def _normalize_confidence(self, score: float) -> float:
        """Normalize confidence score to 0-1 range (AI may return 1-5 scale)."""
        if score > 1.0:
            # Assume 1-5 scale, convert to 0-1
            return min(1.0, score / 5.0)
        return max(0.0, min(1.0, score))
