"""Saved suggestion database model for user-bookmarked meal suggestions."""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.infra.database.config import Base


class SavedSuggestionModel(Base):
    """Persisted user-saved meal suggestions with full suggestion JSON."""

    __tablename__ = "saved_suggestions"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    suggestion_id = Column(String(64), nullable=False)
    meal_type = Column(String(20), nullable=False)
    portion_multiplier = Column(Integer, default=1)
    suggestion_data = Column(JSON, nullable=False)
    dish_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    language = Column(String(10), nullable=True)
    saved_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    items = relationship(
        "SavedSuggestionItemModel",
        back_populates="saved_suggestion",
        cascade="all, delete-orphan",
        order_by="SavedSuggestionItemModel.position",
        lazy="selectin",
    )
    steps = relationship(
        "SavedSuggestionStepModel",
        back_populates="saved_suggestion",
        cascade="all, delete-orphan",
        order_by="SavedSuggestionStepModel.position",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "suggestion_id", name="uq_user_suggestion"),
        Index("idx_user_saved", "user_id", "saved_at"),
    )
