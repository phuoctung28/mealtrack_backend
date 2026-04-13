"""Repository for persisted saved suggestions."""
import logging
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from src.infra.database.models.saved_suggestion import SavedSuggestionModel

logger = logging.getLogger(__name__)


class SavedSuggestionDbRepository:
    """CRUD operations for saved_suggestions table."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_user(self, user_id: str) -> List[SavedSuggestionModel]:
        """Get all saved suggestions for a user, newest first."""
        return (
            self.db.query(SavedSuggestionModel)
            .filter(SavedSuggestionModel.user_id == user_id)
            .order_by(SavedSuggestionModel.saved_at.desc())
            .all()
        )

    def find_by_user_and_suggestion(
        self, user_id: str, suggestion_id: str
    ) -> Optional[SavedSuggestionModel]:
        """Find a specific saved suggestion by user + suggestion ID."""
        return (
            self.db.query(SavedSuggestionModel)
            .filter(
                SavedSuggestionModel.user_id == user_id,
                SavedSuggestionModel.suggestion_id == suggestion_id,
            )
            .first()
        )

    def create(self, model: SavedSuggestionModel) -> SavedSuggestionModel:
        """Insert a new saved suggestion."""
        if not model.id:
            model.id = str(uuid.uuid4())
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def delete_by_user_and_suggestion(
        self, user_id: str, suggestion_id: str
    ) -> bool:
        """Delete a saved suggestion. Returns True if deleted."""
        row = self.find_by_user_and_suggestion(user_id, suggestion_id)
        if row:
            self.db.delete(row)
            self.db.commit()
            return True
        return False

    def count_by_user(self, user_id: str) -> int:
        """Count saved suggestions for a user."""
        return (
            self.db.query(SavedSuggestionModel)
            .filter(SavedSuggestionModel.user_id == user_id)
            .count()
        )
