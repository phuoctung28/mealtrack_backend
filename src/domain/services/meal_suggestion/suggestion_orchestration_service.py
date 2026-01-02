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
from src.domain.services.portion_calculation_service import PortionCalculationService
from src.domain.services.tdee_service import TdeeCalculationService
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
        portion_service: PortionCalculationService = None,
    ):
        self._generation = generation_service
        self._repo = suggestion_repo
        self._user_repo = user_repo
        self._tdee_service = tdee_service or TdeeCalculationService()
        self._portion_service = portion_service or PortionCalculationService()
        self._portion_service = portion_service or PortionCalculationService()

    async def generate_suggestions(
        self,
        user_id: str,
        meal_type: str,
        meal_portion_type: str,
        meal_portion_type: str,
        ingredients: List[str],
        ingredient_image_url: Optional[str],
        cooking_time_minutes: int,
    ) -> Tuple[SuggestionSession, List[MealSuggestion]]:
        """Generate initial 3 suggestions and create session."""
        # Get user's daily TDEE
        user = self._user_repo.find_by_id(user_id)
        if not user or not user.current_profile:
        user = self._user_repo.find_by_id(user_id)
        if not user or not user.current_profile:
            raise ValueError(f"User {user_id} not found or missing profile")

        # Calculate daily TDEE from profile
        daily_tdee = self._calculate_daily_tdee(user.current_profile)

        # Get meals_per_day from profile (default to 3)
        meals_per_day = getattr(user.current_profile, "meals_per_day", 3)

        # Calculate target calories using PortionCalculationService
        portion_target = self._portion_service.get_target_for_meal_type(
            meal_type=meal_portion_type,
            daily_target=int(daily_tdee),
            meals_per_day=meals_per_day,
        )
        target_calories = portion_target.target_calories
        # Get meals_per_day from profile (default to 3)
        meals_per_day = getattr(user.current_profile, "meals_per_day", 3)

        # Calculate target calories using PortionCalculationService
        portion_target = self._portion_service.get_target_for_meal_type(
            meal_type=meal_portion_type,
            daily_target=int(daily_tdee),
            meals_per_day=meals_per_day,
        )
        target_calories = portion_target.target_calories

        # Create session
        session = SuggestionSession(
            id=f"session_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            meal_type=meal_type,
            meal_portion_type=meal_portion_type,
            meal_portion_type=meal_portion_type,
            target_calories=target_calories,
            ingredients=ingredients,
            ingredient_image_url=ingredient_image_url,
            cooking_time_minutes=cooking_time_minutes,
        )

        # Generate with timeout
        suggestions = await self._generate_with_timeout(
            session=session,
            exclude_ids=[],
        )

        # Track shown IDs
        session.add_shown_ids([s.id for s in suggestions])

        # Persist
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
                "maintenance": Goal.MAINTENANCE,
                "cutting": Goal.CUTTING,
                "bulking": Goal.BULKING,
                "recomp": Goal.RECOMP,
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
                activity_level=activity_map.get(
                    profile.activity_level, ActivityLevel.MODERATE
                ),
                goal=goal_map.get(profile.fitness_goal, Goal.MAINTENANCE),
                body_fat_pct=profile.body_fat_percentage,
                unit_system=UnitSystem.METRIC,
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
        """Generate suggestions with timeout, fallback on failure."""
        start_time = time.time()

        try:
            # Build prompt
            prompt = self._build_prompt(session, exclude_ids)
            system_message = "You are a nutrition AI that generates meal suggestions."

            # Log detailed request context
            logger.info(
                f"[MEAL-GEN-START] session={session.id} | "
                f"meal_type={session.meal_type} | "
                f"target_cal={session.target_calories} | "
                f"ingredients={len(session.ingredients or [])} items | "
                f"cook_time={session.cooking_time_minutes}min | "
                f"excluded={len(exclude_ids)} | "
                f"timeout={self.GENERATION_TIMEOUT_SECONDS}s | "
                f"prompt_len={len(prompt)} chars"
            )

            # Call AI with timeout
            # 3 suggestions with full recipe steps need ~8000 tokens
            logger.info(
                f"Generating suggestions for session {session.id}, target: {session.target_calories} cal"
            )
            raw_response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._generation.generate_meal_plan,
                    prompt,
                    system_message,
                    "json",
                    8000,  # Explicit max_tokens for full recipe details
                    8000,  # Explicit max_tokens for full recipe details
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

            # Parse and convert to domain objects
            suggestions = self._parse_ai_response(raw_response, session)

            logger.info(
                f"[MEAL-GEN-PARSED] session={session.id} | "
                f"parsed_count={len(suggestions)} | "
                f"names={[s.meal_name[:30] for s in suggestions]}"
            )

            # Ensure exactly 3 suggestions
            while len(suggestions) < self.SUGGESTIONS_COUNT:
                logger.warning(
                    f"[MEAL-GEN-FALLBACK] session={session.id} | "
                    f"adding fallback suggestion #{len(suggestions) + 1} "
                    f"(only {len(suggestions)}/{self.SUGGESTIONS_COUNT} parsed)"
                )
                suggestions.append(self._create_fallback(session, len(suggestions)))

            return suggestions[: self.SUGGESTIONS_COUNT]
            return suggestions[: self.SUGGESTIONS_COUNT]

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
                self._create_fallback(session, i) for i in range(self.SUGGESTIONS_COUNT)
            ]

    def _build_prompt(self, session: SuggestionSession, exclude_ids: List[str]) -> str:
        """Build AI prompt for meal generation."""
        ingredients_str = (
            ", ".join(session.ingredients)
            if session.ingredients
            else "any common ingredients"
        )
        ingredients_str = (
            ", ".join(session.ingredients)
            if session.ingredients
            else "any common ingredients"
        )
        return f"""Generate exactly 3 meal suggestions for {session.meal_type}.

Requirements:
- Target calories: {session.target_calories} per meal (±10%)
- Available ingredients: {ingredients_str}
- Max cooking time: {session.cooking_time_minutes} minutes
- Excluded meal count: {len(exclude_ids)} (generate different meals)

Return JSON with 'suggestions' array containing exactly 3 objects:
{{
  "suggestions": [
    {{
      "name": "Meal Name",
      "description": "Brief 1-2 sentence description",
      "ingredients": [{{"name": "ingredient", "amount": 100, "unit": "g"}}],
      "recipe_steps": [{{"step": 1, "instruction": "Step text", "duration_minutes": 5}}],
      "macros": {{"calories": 500, "protein": 30, "carbs": 40, "fat": 15}},
      "prep_time_minutes": 20,
      "confidence_score": 0.85
    }}
  ]
}}

IMPORTANT:
- confidence_score must be 0.0-1.0 (not 1-5)
- Include 4-8 recipe_steps per meal
- Macros should match target calories
Return JSON with 'suggestions' array containing exactly 3 objects:
{{
  "suggestions": [
    {{
      "name": "Meal Name",
      "description": "Brief 1-2 sentence description",
      "ingredients": [{{"name": "ingredient", "amount": 100, "unit": "g"}}],
      "recipe_steps": [{{"step": 1, "instruction": "Step text", "duration_minutes": 5}}],
      "macros": {{"calories": 500, "protein": 30, "carbs": 40, "fat": 15}},
      "prep_time_minutes": 20,
      "confidence_score": 0.85
    }}
  ]
}}

IMPORTANT:
- confidence_score must be 0.0-1.0 (not 1-5)
- Include 4-8 recipe_steps per meal
- Macros should match target calories
"""

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
                            calories=raw.get("macros", {}).get(
                                "calories", session.target_calories
                            ),
                            protein=raw.get("macros", {}).get("protein", 20.0),
                            carbs=raw.get("macros", {}).get("carbs", 30.0),
                            fat=raw.get("macros", {}).get("fat", 10.0),
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
