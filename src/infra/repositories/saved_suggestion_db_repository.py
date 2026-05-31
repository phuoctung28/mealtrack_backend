"""Repository for persisted saved suggestions."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.ports.saved_suggestion_repository_port import (
    SavedSuggestionRepositoryPort,
)
from src.infra.database.models.saved_suggestion import SavedSuggestionModel

logger = logging.getLogger(__name__)


def _model_to_dict(model: SavedSuggestionModel) -> Dict[str, Any]:
    """Convert ORM model to plain dict for domain/app layer consumption."""
    return {
        "id": model.id,
        "suggestion_id": model.suggestion_id,
        "catalog_meal_id": getattr(model, "catalog_meal_id", None),
        "source": getattr(model, "source", "generated"),
        "meal_type": model.meal_type,
        "portion_multiplier": model.portion_multiplier,
        "suggestion_data": model.suggestion_data,
        "saved_at": model.saved_at.isoformat() if model.saved_at else None,
    }


class SavedSuggestionDbRepository(SavedSuggestionRepositoryPort):
    """CRUD operations for saved_suggestions table."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all saved suggestions for a user, newest first."""
        rows = (
            self.db.query(SavedSuggestionModel)
            .filter(SavedSuggestionModel.user_id == user_id)
            .order_by(SavedSuggestionModel.saved_at.desc())
            .all()
        )
        return [_model_to_dict(r) for r in rows]

    def find_by_user_and_source(
        self, user_id: str, source: str
    ) -> List[Dict[str, Any]]:
        """Get saved suggestions for a user by source."""
        rows = (
            self.db.query(SavedSuggestionModel)
            .filter(
                SavedSuggestionModel.user_id == user_id,
                SavedSuggestionModel.source == source,
            )
            .order_by(SavedSuggestionModel.saved_at.desc())
            .all()
        )
        return [_model_to_dict(r) for r in rows]

    def find_by_user_and_suggestion(
        self, user_id: str, suggestion_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a specific saved suggestion by user + suggestion ID."""
        row = (
            self.db.query(SavedSuggestionModel)
            .filter(
                SavedSuggestionModel.user_id == user_id,
                SavedSuggestionModel.suggestion_id == suggestion_id,
            )
            .first()
        )
        return _model_to_dict(row) if row else None

    def save(
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
        self.db.add(model)
        self.db.flush()
        return _model_to_dict(model)

    def upsert_from_catalog(
        self,
        user_id: str,
        meal: Any,
    ) -> Dict[str, Any]:
        """Save a catalog meal as a saved suggestion, idempotent per user/meal."""
        now = datetime.now(timezone.utc)
        row = (
            self.db.query(SavedSuggestionModel)
            .filter(
                SavedSuggestionModel.user_id == user_id,
                SavedSuggestionModel.catalog_meal_id == meal.id,
            )
            .first()
        )
        suggestion_data = {
            "id": meal.id,
            "meal_name": meal.meal_name,
            "english_name": meal.english_name,
            "calories": meal.calories,
            "protein_g": meal.protein_g,
            "carbs_g": meal.carbs_g,
            "fat_g": meal.fat_g,
            "ingredients": meal.ingredients,
            "recipe_steps": meal.recipe_steps,
            "image_url": meal.image_url,
            "thumbnail_url": meal.thumbnail_url,
        }
        if row:
            row.suggestion_data = suggestion_data
            row.saved_at = now
            self.db.flush()
            return _model_to_dict(row)

        model = SavedSuggestionModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            suggestion_id=f"catalog:{meal.id}",
            catalog_meal_id=meal.id,
            source="catalog",
            meal_type=(meal.meal_types or ["unknown"])[0],
            portion_multiplier=1,
            suggestion_data=suggestion_data,
            saved_at=now,
            created_at=now,
        )
        self.db.add(model)
        self.db.flush()
        return _model_to_dict(model)

    def create(self, model: SavedSuggestionModel) -> SavedSuggestionModel:
        """Insert a new saved suggestion (legacy ORM-based method)."""
        if not model.id:
            model.id = str(uuid.uuid4())
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def delete_by_user_and_suggestion(self, user_id: str, suggestion_id: str) -> bool:
        """Delete a saved suggestion. Returns True if deleted."""
        row = (
            self.db.query(SavedSuggestionModel)
            .filter(
                SavedSuggestionModel.user_id == user_id,
                SavedSuggestionModel.suggestion_id == suggestion_id,
            )
            .first()
        )
        if row:
            self.db.delete(row)
            return True
        return False

    def count_by_user(self, user_id: str) -> int:
        """Count saved suggestions for a user."""
        return (
            self.db.query(SavedSuggestionModel)
            .filter(SavedSuggestionModel.user_id == user_id)
            .count()
        )
