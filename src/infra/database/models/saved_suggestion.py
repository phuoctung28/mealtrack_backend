"""Saved suggestion database model for user-bookmarked meal suggestions."""
from sqlalchemy import Column, String, Integer, DateTime, JSON, UniqueConstraint, Index

from src.infra.database.config import Base


class SavedSuggestionModel(Base):
    """Persisted user-saved meal suggestions with full suggestion JSON."""

    __tablename__ = "saved_suggestions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(128), nullable=False)
    suggestion_id = Column(String(64), nullable=False)
    meal_type = Column(String(20), nullable=False)
    portion_multiplier = Column(Integer, default=1)
    suggestion_data = Column(JSON, nullable=False)
    saved_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'suggestion_id', name='uq_user_suggestion'),
        Index('idx_user_saved', 'user_id', 'saved_at'),
    )
