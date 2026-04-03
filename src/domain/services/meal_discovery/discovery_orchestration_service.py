"""
Orchestration service for meal discovery batch generation (NM-67).
Handles profile fetch, TDEE calc, AI generation, parsing, and session tracking.
Sessions are stored in-memory with TTL cleanup (no DB required for Phase 1).
"""
import json
import logging
import re
import time
import uuid
from datetime import timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.domain.model.meal_discovery import DiscoveryMeal, DiscoverySession
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.meal_discovery.discovery_prompt_builder import build_discovery_prompt
from src.domain.services.meal_suggestion.suggestion_tdee_helpers import (
    get_adjusted_daily_target,
    calculate_daily_tdee,
)
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)

SESSION_TTL_HOURS = 4
MAX_SESSIONS = 10_000  # cap in-memory dict


class DiscoveryOrchestrationService:
    """
    Orchestrates discovery batch generation.
    Singleton-safe: sessions stored in class-level dict with lazy TTL cleanup.
    """

    _sessions: Dict[str, Tuple[DiscoverySession, float]] = {}  # {id: (session, expires_ts)}

    def __init__(
        self,
        generation_service: MealGenerationServicePort,
        profile_provider: Callable[[str], Any],
        uow_factory: Callable[[], Any],
        tdee_service: Optional[TdeeCalculationService] = None,
    ):
        self._generation = generation_service
        self._profile_provider = profile_provider
        self._uow_factory = uow_factory
        self._tdee_service = tdee_service or TdeeCalculationService()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def generate(
        self,
        user_id: str,
        meal_type: Optional[str] = None,
        cuisine_filter: Optional[str] = None,
        exclude_ids: Optional[List[str]] = None,
        language: str = "en",
        session_id: Optional[str] = None,
    ) -> Tuple[DiscoverySession, List[DiscoveryMeal]]:
        """Generate a batch of 15 discovery meals, returning session + meals."""

        # Load or create session
        session = self._get_or_create_session(user_id, session_id)

        # Fetch profile
        try:
            profile = self._profile_provider(user_id)
        except Exception as e:
            logger.warning(f"Could not fetch profile for {user_id}: {e}")
            profile = None

        # Determine remaining calories
        remaining_calories = await self._get_remaining_calories(user_id, profile)

        # Derive user preferences from profile
        allergies: List[str] = getattr(profile, "allergies", None) or []
        dietary_preferences: List[str] = getattr(profile, "dietary_preferences", None) or []
        disliked_foods: List[str] = getattr(profile, "disliked_foods", None) or []

        # Build exclude list from session history + explicit exclude_ids
        exclude_names = list(session.shown_meal_names)

        # Build and execute prompt
        prompt = build_discovery_prompt(
            remaining_calories=remaining_calories,
            meal_type=meal_type,
            cuisine_filter=cuisine_filter,
            exclude_names=exclude_names,
            allergies=allergies,
            dietary_preferences=dietary_preferences,
            disliked_foods=disliked_foods,
            language=language,
        )

        meals = await self._generate_meals(prompt)

        # Update session with newly shown meals
        for meal in meals:
            session.shown_meal_ids.append(meal.id)
            session.shown_meal_names.append(meal.name_en)

        self._save_session(session)

        return session, meals

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_remaining_calories(self, user_id: str, profile: Any) -> float:
        """Return remaining daily calories. Falls back to daily target if UoW fails."""
        if profile is None:
            return 2000.0
        try:
            with self._uow_factory() as uow:
                daily_target = await get_adjusted_daily_target(
                    self._tdee_service, user_id, profile, uow=uow
                )
            return max(300.0, daily_target)
        except Exception as e:
            logger.warning(f"Failed adjusted target for {user_id}: {e}")
            return max(300.0, calculate_daily_tdee(self._tdee_service, profile))

    async def _generate_meals(self, prompt: str) -> List[DiscoveryMeal]:
        """Call AI, parse response, return validated DiscoveryMeal list."""
        try:
            result = self._generation.generate_meal_plan(
                prompt=prompt,
                system_message="You are a meal discovery engine. Generate diverse meal ideas as JSON.",
                response_type="json",
            )
            # generate_meal_plan returns Dict when response_type="json"
            if isinstance(result, dict):
                raw_meals = result.get("meals", [])
            elif isinstance(result, str):
                data = self._extract_json(result)
                raw_meals = data.get("meals", [])
            else:
                raw_meals = []
            return [m for m in (self._parse_single_meal(item) for item in raw_meals) if m]
        except Exception as e:
            logger.error(f"Discovery generation failed: {e}")
            return []

    def _parse_meals(self, content: str) -> List[DiscoveryMeal]:
        """Extract and validate meals from AI JSON response."""
        try:
            data = self._extract_json(content)
            raw_meals = data.get("meals", [])
            meals: List[DiscoveryMeal] = []
            for item in raw_meals:
                meal = self._parse_single_meal(item)
                if meal:
                    meals.append(meal)
            return meals
        except Exception as e:
            logger.error(f"Failed to parse discovery meals: {e}")
            return []

    def _parse_single_meal(self, item: Dict) -> Optional[DiscoveryMeal]:
        """Parse one meal dict, validate macros, return DiscoveryMeal or None."""
        try:
            protein = float(item.get("protein", 0))
            carbs = float(item.get("carbs", 0))
            fat = float(item.get("fat", 0))
            calories = int(item.get("calories", 0))

            # Macro validation: recalculate if >15% off
            derived = protein * 4 + carbs * 4 + fat * 9
            if calories > 0 and abs(derived - calories) / calories > 0.15:
                calories = round(derived)

            return DiscoveryMeal(
                id=str(uuid.uuid4()),
                name=str(item.get("name", "")),
                name_en=str(item.get("name_en", item.get("name", ""))),
                emoji=str(item.get("emoji", "🍽️")),
                cuisine=str(item.get("cuisine", "International")),
                calories=max(0, calories),
                protein=max(0.0, protein),
                carbs=max(0.0, carbs),
                fat=max(0.0, fat),
                ingredients=list(item.get("ingredients", [])),
                image_search_query=str(item.get("image_search_query", "")),
            )
        except Exception as e:
            logger.warning(f"Skipping malformed meal item: {e}")
            return None

    @staticmethod
    def _extract_json(content: str) -> Dict:
        """Extract JSON dict from AI response (handles markdown code blocks)."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```json(.*?)```", content, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("Could not extract JSON from AI response")

    # ------------------------------------------------------------------
    # Session management (in-memory with TTL)
    # ------------------------------------------------------------------

    def _get_or_create_session(self, user_id: str, session_id: Optional[str]) -> DiscoverySession:
        """Return existing valid session or create new one."""
        if session_id:
            entry = DiscoveryOrchestrationService._sessions.get(session_id)
            if entry:
                session, expires_ts = entry
                if time.time() < expires_ts and session.user_id == user_id:
                    return session
        return self._create_session(user_id)

    def _create_session(self, user_id: str) -> DiscoverySession:
        self._evict_expired()
        now = utc_now()
        session = DiscoverySession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(hours=SESSION_TTL_HOURS),
        )
        return session

    def _save_session(self, session: DiscoverySession) -> None:
        expires_ts = time.time() + SESSION_TTL_HOURS * 3600
        DiscoveryOrchestrationService._sessions[session.id] = (session, expires_ts)

    @classmethod
    def _evict_expired(cls) -> None:
        """Remove expired sessions; also cap dict size with oldest-first eviction."""
        now = time.time()
        expired = [k for k, (_, ts) in cls._sessions.items() if now >= ts]
        for k in expired:
            del cls._sessions[k]
        # If still over cap, remove oldest entries
        if len(cls._sessions) >= MAX_SESSIONS:
            sorted_keys = sorted(cls._sessions, key=lambda k: cls._sessions[k][1])
            for k in sorted_keys[: len(cls._sessions) - MAX_SESSIONS + 1]:
                del cls._sessions[k]
