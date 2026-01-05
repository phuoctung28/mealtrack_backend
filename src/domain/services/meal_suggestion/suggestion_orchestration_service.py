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
    MEAL_SIZE_PERCENTAGES,
    MacroEstimate,
    Ingredient,
    RecipeStep,
    MealType,
)
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.ports.meal_suggestion_repository_port import (
    MealSuggestionRepositoryPort,
)
from src.domain.ports.meal_suggestion_repository_port import (
    MealSuggestionRepositoryPort,
)
from src.domain.ports.user_repository_port import UserRepositoryPort
from src.domain.services.portion_calculation_service import PortionCalculationService
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.services.meal_suggestion.nutrition_enrichment_service import NutritionEnrichmentService
from src.domain.services.meal_suggestion.recipe_search_service import RecipeSearchService, RecipeSearchCriteria
from src.domain.model.user import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem

logger = logging.getLogger(__name__)


class SuggestionOrchestrationService:
    """
    Orchestrates meal suggestion generation with session tracking.
    Implements timeout handling, fallback logic, and portion multipliers.
    """

    GENERATION_TIMEOUT_SECONDS = 45  # Increased from 30s - full recipe generation needs ~30-35s
    SUGGESTIONS_COUNT = 3

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        suggestion_repo: MealSuggestionRepositoryPort,
        user_repo: UserRepositoryPort,
        tdee_service: TdeeCalculationService = None,
        portion_service: PortionCalculationService = None,
        nutrition_enrichment: NutritionEnrichmentService = None,
        recipe_search: RecipeSearchService = None,
        redis_client=None,
    ):
        self._generation = generation_service
        self._repo = suggestion_repo
        self._user_repo = user_repo
        self._tdee_service = tdee_service or TdeeCalculationService()
        self._portion_service = portion_service or PortionCalculationService()
        self._nutrition_enrichment = nutrition_enrichment or NutritionEnrichmentService()
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
            logger.warning(
                f"Failed to calculate TDEE: {e}. Using default 2000 calories."
            )
            return 2000.0

    async def _generate_with_timeout(
        self,
        session: SuggestionSession,
        exclude_ids: List[str],
    ) -> List[MealSuggestion]:
        """Generate suggestions with hybrid retrieval (Pinecone + AI fallback)."""
        start_time = time.time()

        try:
            # PHASE 2: Try Pinecone recipe search first (fast path)
            if self._recipe_search:
                logger.info(
                    f"[RECIPE-SEARCH-ATTEMPT] session={session.id} | "
                    f"meal_type={session.meal_type} | target_cal={session.target_calories}"
                )

                criteria = RecipeSearchCriteria(
                    meal_type=session.meal_type,
                    target_calories=session.target_calories,
                    calorie_tolerance=100,
                    max_cook_time=session.cooking_time_minutes,
                    dietary_preferences=getattr(session, 'dietary_preferences', []),
                    allergies=getattr(session, 'allergies', []),
                    ingredients=session.ingredients,
                    exclude_ids=exclude_ids
                )

                # Wrap synchronous blocking call to avoid event loop blocking
                # search_recipes performs CPU-bound embedding generation and network I/O
                recipes = await asyncio.to_thread(
                    self._recipe_search.search_recipes,
                    criteria=criteria,
                    top_k=10  # Get 10 candidates
                )

                if len(recipes) >= 3:
                    elapsed = time.time() - start_time
                    logger.info(
                        f"[RECIPE-SEARCH-SUCCESS] session={session.id} | "
                        f"found={len(recipes)} recipes | elapsed={elapsed:.2f}s | Using top 3"
                    )
                    # Convert to MealSuggestion objects
                    suggestions = [
                        self._recipe_to_suggestion(recipe, session)
                        for recipe in recipes[:3]
                    ]
                    return suggestions
                else:
                    logger.info(
                        f"[RECIPE-SEARCH-INSUFFICIENT] session={session.id} | "
                        f"Only {len(recipes)}/3 recipes found | Falling back to AI generation"
                    )

            # PHASE 1: AI generation fallback (slow path)
            return await self._generate_with_ai(session, exclude_ids, start_time)

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[GENERATION-ERROR] session={session.id} | "
                f"elapsed={elapsed:.2f}s | error={str(e)[:200]}",
                exc_info=True
            )
            return [
                self._create_fallback(session, i) for i in range(self.SUGGESTIONS_COUNT)
            ]

    async def _generate_with_ai(
        self,
        session: SuggestionSession,
        exclude_ids: List[str],
        start_time: float
    ) -> List[MealSuggestion]:
        """AI generation path (existing logic)."""
        try:
            # Build prompt
            prompt = self._build_prompt(session, exclude_ids)
            system_message = "You are a nutrition AI that generates meal suggestions."

            # Log detailed request context
            logger.info(
                f"[AI-GENERATION] session={session.id} | "
                f"meal_type={session.meal_type} | "
                f"target_cal={session.target_calories} | "
                f"ingredients={len(session.ingredients or [])} items | "
                f"cook_time={session.cooking_time_minutes}min | "
                f"excluded={len(exclude_ids)} | "
                f"timeout={self.GENERATION_TIMEOUT_SECONDS}s | "
                f"prompt_len={len(prompt)} chars"
            )

            # Call AI with timeout (Phase 1: reduced tokens - no macros)
            logger.info(
                f"Generating suggestions for session {session.id}, target: {session.target_calories} cal"
            )
            raw_response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._generation.generate_meal_plan,
                    prompt,
                    system_message,
                    "json",
                    4000,  # Reduced from 8000 (Phase 1: AI doesn't generate macros)
                ),
                timeout=self.GENERATION_TIMEOUT_SECONDS,
            )

            elapsed = time.time() - start_time
            logger.info(
                f"[MEAL-GEN-RESPONSE] session={session.id} | "
                f"elapsed={elapsed:.2f}s | "
                f"response_keys={list(raw_response.keys()) if isinstance(raw_response, dict) else 'non-dict'} | "
                f"suggestions_count={len(raw_response.get('suggestions', []))} "
            )

            # Parse AI response (now without macros)
            raw_suggestions = self._parse_ai_response(raw_response, session)

            # Phase 1 optimization: Enrich with nutrition calculation
            enriched_suggestions = []
            for suggestion in raw_suggestions:
                enrichment = self._nutrition_enrichment.calculate_meal_nutrition(
                    ingredients=suggestion.ingredients,
                    target_calories=session.target_calories
                )

                # Update suggestion with calculated macros
                suggestion.macros = enrichment.macros
                suggestion.confidence_score = min(
                    suggestion.confidence_score,
                    enrichment.confidence_score
                )

                if enrichment.missing_ingredients:
                    logger.debug(
                        f"Missing nutrition data for {len(enrichment.missing_ingredients)} ingredients: "
                        f"{', '.join(enrichment.missing_ingredients[:3])}"
                    )

                enriched_suggestions.append(suggestion)

            logger.info(
                f"[MEAL-GEN-ENRICHED] session={session.id} | "
                f"enriched_count={len(enriched_suggestions)} | "
                f"names={[s.meal_name[:30] for s in enriched_suggestions]}"
            )

            # Ensure exactly 3 suggestions
            while len(enriched_suggestions) < self.SUGGESTIONS_COUNT:
                logger.warning(
                    f"[MEAL-GEN-FALLBACK] session={session.id} | "
                    f"adding fallback suggestion #{len(enriched_suggestions) + 1} "
                    f"(only {len(enriched_suggestions)}/{self.SUGGESTIONS_COUNT} parsed)"
                )
                enriched_suggestions.append(self._create_fallback(session, len(enriched_suggestions)))

            return enriched_suggestions[: self.SUGGESTIONS_COUNT]

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.warning(
                f"[MEAL-GEN-TIMEOUT] session={session.id} | "
                f"timeout={self.GENERATION_TIMEOUT_SECONDS}s | "
                f"elapsed={elapsed:.2f}s | "
                f"meal_type={session.meal_type} | "
                f"ingredients={session.ingredients[:5] if session.ingredients else []}... | "
                f"Returning fallback suggestions."
            )
            return [
                self._create_fallback(session, i) for i in range(self.SUGGESTIONS_COUNT)
            ]
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[MEAL-GEN-ERROR] session={session.id} | "
                f"elapsed={elapsed:.2f}s | "
                f"error_type={type(e).__name__} | "
                f"error={str(e)[:200]}",
                exc_info=True,
            )
            return [
                self._create_fallback(session, i) for i in range(self.SUGGESTIONS_COUNT)
            ]

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

    def _create_fallback(
        self, session: SuggestionSession, index: int
    ) -> MealSuggestion:
        """Create fallback suggestion when AI fails."""
        return MealSuggestion(
            id=f"fallback_{uuid.uuid4().hex[:8]}",
            session_id=session.id,
            user_id=session.user_id,
            meal_name=f"Simple {session.meal_type.title()} #{index + 1}",
            description="Quick and nutritious meal",
            meal_type=MealType(session.meal_type),
            macros=MacroEstimate(
                calories=session.target_calories,
                protein=session.target_calories * 0.3 / 4,
                carbs=session.target_calories * 0.4 / 4,
                fat=session.target_calories * 0.3 / 9,
            ),
            ingredients=[
                Ingredient(name="Protein source", amount=150, unit="g"),
                Ingredient(name="Vegetables", amount=100, unit="g"),
                Ingredient(name="Grains", amount=100, unit="g"),
            ],
            recipe_steps=[
                RecipeStep(
                    step=1, instruction="Prepare ingredients", duration_minutes=5
                ),
                RecipeStep(
                    step=1, instruction="Prepare ingredients", duration_minutes=5
                ),
                RecipeStep(step=2, instruction="Cook meal", duration_minutes=15),
            ],
            prep_time_minutes=20,
            confidence_score=0.5,
        )

    def _normalize_confidence(self, score: float) -> float:
        """Normalize confidence score to 0-1 range (AI may return 1-5 scale)."""
        if score > 1.0:
            # Assume 1-5 scale, convert to 0-1
            return min(1.0, score / 5.0)
        return max(0.0, min(1.0, score))

    def _normalize_confidence(self, score: float) -> float:
        """Normalize confidence score to 0-1 range (AI may return 1-5 scale)."""
        if score > 1.0:
            # Assume 1-5 scale, convert to 0-1
            return min(1.0, score / 5.0)
        return max(0.0, min(1.0, score))
