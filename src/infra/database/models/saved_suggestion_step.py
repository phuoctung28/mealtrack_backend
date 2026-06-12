"""Normalized cooking-step rows for saved meal suggestions."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from src.infra.database.base import Base


class SavedSuggestionStepModel(Base):
    """Queryable recipe step snapshot for a saved suggestion."""

    __tablename__ = "saved_suggestion_steps"

    id = Column(String(36), primary_key=True)
    saved_suggestion_id = Column(
        String(36),
        ForeignKey("saved_suggestions.id", ondelete="CASCADE"),
        nullable=False,
    )
    instruction = Column(Text, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    position = Column(Integer, nullable=False)

    saved_suggestion = relationship("SavedSuggestionModel", back_populates="steps")

    __table_args__ = (
        Index(
            "idx_saved_suggestion_steps_suggestion_position",
            "saved_suggestion_id",
            "position",
        ),
    )
