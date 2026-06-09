"""Normalized ingredient rows for saved meal suggestions."""

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from src.infra.database.config import Base


class SavedSuggestionItemModel(Base):
    """Queryable ingredient snapshot for a saved suggestion."""

    __tablename__ = "saved_suggestion_items"

    id = Column(String(36), primary_key=True)
    saved_suggestion_id = Column(
        String(36),
        ForeignKey("saved_suggestions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=True)
    unit = Column(String(64), nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    position = Column(Integer, nullable=False)

    saved_suggestion = relationship("SavedSuggestionModel", back_populates="items")

    __table_args__ = (
        Index(
            "idx_saved_suggestion_items_suggestion_position",
            "saved_suggestion_id",
            "position",
        ),
    )
