"""Async repository for persisted saved suggestions."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database.models.saved_suggestion import SavedSuggestionModel

logger = logging.getLogger(__name__)


def _model_to_dict(model: SavedSuggestionModel) -> Dict[str, Any]:
    """Convert ORM model to plain dict for domain/app layer consumption."""
    return {
        "id": model.id,
        "suggestion_id": model.suggestion_id,
        "meal_type": model.meal_type,
        "portion_multiplier": model.portion_multiplier,
        "suggestion_data": model.suggestion_data,
        "saved_at": model.saved_at.isoformat() if model.saved_at else None,
    }


class AsyncSavedSuggestionDbRepository:
    """Async CRUD operations for saved_suggestions table. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all saved suggestions for a user, newest first."""
        result = await self.session.execute(
            select(SavedSuggestionModel)
            .where(SavedSuggestionModel.user_id == user_id)
            .order_by(SavedSuggestionModel.saved_at.desc())
        )
        return [_model_to_dict(r) for r in result.scalars().all()]

    async def find_by_user_and_suggestion(
        self, user_id: str, suggestion_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a specific saved suggestion by user + suggestion ID."""
        result = await self.session.execute(
            select(SavedSuggestionModel).where(
                SavedSuggestionModel.user_id == user_id,
                SavedSuggestionModel.suggestion_id == suggestion_id,
            )
        )
        row = result.scalars().first()
        return _model_to_dict(row) if row else None

    async def save(
        self,
        user_id: str,
        suggestion_id: str,
        meal_type: str,
        portion_multiplier: float,
        suggestion_data: dict,
    ) -> Dict[str, Any]:
        """Save a new suggestion. Returns the saved record as a dict."""
        now = datetime.now(timezone.utc)
        model = SavedSuggestionModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            suggestion_id=suggestion_id,
            meal_type=meal_type,
            portion_multiplier=portion_multiplier,
            suggestion_data=suggestion_data,
            saved_at=now,
            created_at=now,
        )
        self.session.add(model)
        await self.session.flush()
        return _model_to_dict(model)

    async def create(self, model: SavedSuggestionModel) -> SavedSuggestionModel:
        """Insert a new saved suggestion (legacy ORM-based method)."""
        if not model.id:
            model.id = str(uuid.uuid4())
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_by_user_and_suggestion(
        self, user_id: str, suggestion_id: str
    ) -> bool:
        """Delete a saved suggestion. Returns True if deleted."""
        result = await self.session.execute(
            select(SavedSuggestionModel).where(
                SavedSuggestionModel.user_id == user_id,
                SavedSuggestionModel.suggestion_id == suggestion_id,
            )
        )
        row = result.scalars().first()
        if row:
            await self.session.delete(row)
            return True
        return False

    async def count_by_user(self, user_id: str) -> int:
        """Count saved suggestions for a user."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count())
            .select_from(SavedSuggestionModel)
            .where(SavedSuggestionModel.user_id == user_id)
        )
        return result.scalar_one()
