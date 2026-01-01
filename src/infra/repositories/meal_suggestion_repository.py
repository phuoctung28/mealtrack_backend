"""Redis-backed meal suggestion repository (Phase 06)."""
import json
import logging
from typing import List, Optional

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.domain.ports.meal_suggestion_repository_port import MealSuggestionRepositoryPort
from src.infra.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)


class MealSuggestionRepository(MealSuggestionRepositoryPort):
    """Redis-backed repository for meal suggestions with 4-hour TTL."""

    TTL_SECONDS = 4 * 60 * 60  # 4 hours

    def __init__(self, redis_client: RedisClient):
        self._cache = redis_client

    async def save_session(self, session: SuggestionSession) -> None:
        """Save session with 4-hour TTL."""
        key = f"suggestion_session:{session.id}"
        data = self._serialize_session(session)
        await self._cache.set(key, data, ttl=self.TTL_SECONDS)
        logger.debug(f"Saved session {session.id}")

    async def get_session(self, session_id: str) -> Optional[SuggestionSession]:
        """Retrieve session by ID."""
        key = f"suggestion_session:{session_id}"
        data = await self._cache.get(key)
        if not data:
            return None
        return self._deserialize_session(data)

    async def update_session(self, session: SuggestionSession) -> None:
        """Update session (maintains remaining TTL)."""
        key = f"suggestion_session:{session.id}"
        # Get remaining TTL
        if self._cache.client:
            ttl = await self._cache.client.ttl(key)
            if ttl <= 0:
                ttl = self.TTL_SECONDS
        else:
            ttl = self.TTL_SECONDS

        data = self._serialize_session(session)
        await self._cache.set(key, data, ttl=ttl)
        logger.debug(f"Updated session {session.id}")

    async def delete_session(self, session_id: str) -> None:
        """Delete session and all associated suggestions."""
        session_key = f"suggestion_session:{session_id}"
        await self._cache.delete(session_key)

        # Delete all suggestions for this session
        pattern = f"suggestion:{session_id}:*"
        deleted_count = await self._cache.delete_pattern(pattern)
        logger.debug(f"Deleted session {session_id} and {deleted_count} suggestions")

    async def save_suggestions(self, suggestions: List[MealSuggestion]) -> None:
        """Save batch of suggestions with 4-hour TTL."""
        for suggestion in suggestions:
            key = f"suggestion:{suggestion.session_id}:{suggestion.id}"
            data = self._serialize_suggestion(suggestion)
            await self._cache.set(key, data, ttl=self.TTL_SECONDS)
        logger.debug(f"Saved {len(suggestions)} suggestions")

    async def get_suggestion(self, suggestion_id: str) -> Optional[MealSuggestion]:
        """Retrieve single suggestion by ID."""
        # Search across all sessions (not ideal but works for 4h TTL)
        pattern = f"suggestion:*:{suggestion_id}"
        if not self._cache.client:
            return None

        keys = await self._cache.client.keys(pattern)
        if not keys:
            return None

        data = await self._cache.get(keys[0])
        if not data:
            return None

        return self._deserialize_suggestion(data)

    async def update_suggestion(self, suggestion: MealSuggestion) -> None:
        """Update suggestion (e.g., status change)."""
        key = f"suggestion:{suggestion.session_id}:{suggestion.id}"
        if self._cache.client:
            ttl = await self._cache.client.ttl(key)
            if ttl <= 0:
                ttl = self.TTL_SECONDS
        else:
            ttl = self.TTL_SECONDS

        data = self._serialize_suggestion(suggestion)
        await self._cache.set(key, data, ttl=ttl)
        logger.debug(f"Updated suggestion {suggestion.id}")

    async def get_session_suggestions(
        self, session_id: str
    ) -> List[MealSuggestion]:
        """Get all suggestions for a session."""
        pattern = f"suggestion:{session_id}:*"
        if not self._cache.client:
            return []

        keys = await self._cache.client.keys(pattern)
        if not keys:
            return []

        suggestions = []
        for key in keys:
            data = await self._cache.get(key)
            if data:
                suggestions.append(self._deserialize_suggestion(data))

        return suggestions

    def _serialize_session(self, session: SuggestionSession) -> str:
        """Serialize session to JSON string."""
        return json.dumps({
            "id": session.id,
            "user_id": session.user_id,
            "meal_type": session.meal_type,
            "meal_portion_type": session.meal_portion_type,
            "target_calories": session.target_calories,
            "ingredients": session.ingredients,
            "ingredient_image_url": session.ingredient_image_url,
            "cooking_time_minutes": session.cooking_time_minutes,
            "shown_suggestion_ids": session.shown_suggestion_ids,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        })

    def _deserialize_session(self, data: str) -> SuggestionSession:
        """Deserialize JSON to session object."""
        from datetime import datetime
        obj = json.loads(data)
        return SuggestionSession(
            id=obj["id"],
            user_id=obj["user_id"],
            meal_type=obj["meal_type"],
            meal_size=obj["meal_size"],
            target_calories=obj["target_calories"],
            ingredients=obj["ingredients"],
            ingredient_image_url=obj.get("ingredient_image_url"),
            cooking_time_minutes=obj["cooking_time_minutes"],
            shown_suggestion_ids=obj.get("shown_suggestion_ids", []),
            created_at=datetime.fromisoformat(obj["created_at"]),
            expires_at=datetime.fromisoformat(obj["expires_at"]) if obj.get("expires_at") else None,
        )

    def _serialize_suggestion(self, suggestion: MealSuggestion) -> str:
        """Serialize suggestion to JSON string."""
        return json.dumps({
            "id": suggestion.id,
            "session_id": suggestion.session_id,
            "user_id": suggestion.user_id,
            "meal_name": suggestion.meal_name,
            "description": suggestion.description,
            "meal_type": suggestion.meal_type.value,
            "macros": {
                "calories": suggestion.macros.calories,
                "protein": suggestion.macros.protein,
                "carbs": suggestion.macros.carbs,
                "fat": suggestion.macros.fat,
            },
            "ingredients": [
                {"name": ing.name, "amount": ing.amount, "unit": ing.unit}
                for ing in suggestion.ingredients
            ],
            "recipe_steps": [
                {"step": step.step, "instruction": step.instruction, "duration_minutes": step.duration_minutes}
                for step in suggestion.recipe_steps
            ],
            "prep_time_minutes": suggestion.prep_time_minutes,
            "confidence_score": suggestion.confidence_score,
            "status": suggestion.status.value,
            "generated_at": suggestion.generated_at.isoformat(),
        })

    def _deserialize_suggestion(self, data: str) -> MealSuggestion:
        """Deserialize JSON to suggestion object."""
        from datetime import datetime
        from src.domain.model.meal_suggestion import (
            MealType,
            SuggestionStatus,
            MacroEstimate,
            Ingredient,
            RecipeStep,
        )

        obj = json.loads(data)
        return MealSuggestion(
            id=obj["id"],
            session_id=obj["session_id"],
            user_id=obj["user_id"],
            meal_name=obj["meal_name"],
            description=obj["description"],
            meal_type=MealType(obj["meal_type"]),
            macros=MacroEstimate(**obj["macros"]),
            ingredients=[Ingredient(**ing) for ing in obj["ingredients"]],
            recipe_steps=[RecipeStep(**step) for step in obj["recipe_steps"]],
            prep_time_minutes=obj["prep_time_minutes"],
            confidence_score=obj["confidence_score"],
            status=SuggestionStatus(obj["status"]),
            generated_at=datetime.fromisoformat(obj["generated_at"]),
        )
