"""
Meal model for the main meal entity.
"""
from sqlalchemy import Column, String, Text, Enum, ForeignKey, DateTime, Integer, Boolean, JSON
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import TimestampMixin
from src.infra.database.models.enums import MealStatusEnum


class MealORM(Base, TimestampMixin):
    """Database model for meals."""

    __tablename__ = 'meal'

    # Primary key
    meal_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)  # User who created this meal
    status = Column(Enum(MealStatusEnum, native_enum=False), nullable=False)
    dish_name = Column(String(255), nullable=True)  # The name of the dish
    meal_type = Column(String(20), nullable=True)  # breakfast, lunch, dinner, snack
    ready_at = Column(DateTime(timezone=True), nullable=True)  # When meal analysis was completed
    error_message = Column(Text, nullable=True)
    raw_ai_response = Column(Text, nullable=True)

    # Edit tracking fields
    last_edited_at = Column(DateTime(timezone=True), nullable=True)  # When meal was last edited
    edit_count = Column(Integer, default=0, nullable=False)  # Number of times edited
    is_manually_edited = Column(Boolean, default=False, nullable=False)  # Whether meal has been manually edited

    # Source tracking (scanner, prompt, food_search, manual)
    source = Column(String(20), nullable=True)

    # Recipe details (populated for AI suggestions)
    description = Column(Text, nullable=True)
    instructions = Column(JSON, nullable=True)  # List[str]
    prep_time_min = Column(Integer, nullable=True)
    cook_time_min = Column(Integer, nullable=True)
    cuisine_type = Column(String(50), nullable=True)
    origin_country = Column(String(50), nullable=True)
    emoji = Column(String(8), nullable=True)  # AI-assigned food emoji

    # Relationships
    image_id = Column(String(36), ForeignKey("mealimage.image_id"), nullable=False)
    image = relationship("MealImageORM", uselist=False, lazy="joined")
    nutrition = relationship("NutritionORM", uselist=False, back_populates="meal",
                             cascade="all, delete-orphan", lazy="raise")
    translations = relationship(
        "MealTranslationORM",
        back_populates="meal",
        cascade="all, delete-orphan",
        lazy="selectin"
    )