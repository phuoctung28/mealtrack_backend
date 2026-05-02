"""
Meal translation database models.

Stores translated content separately from original English to support
multiple languages.
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

from src.infra.database.config import Base


class MealTranslationORM(Base):
    """
    Database model for meal translations.

    Stores translated dish_name for each language.
    """

    __tablename__ = "meal_translation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(
        String(36), ForeignKey("meal.meal_id"), nullable=True, index=True
    )  # Nullable to prevent cascade delete
    language = Column(
        String(7), nullable=False
    )  # ISO 639-1: en, vi, es, fr, de, ja, zh
    dish_name = Column(String(255), nullable=False)
    translated_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    meal_instruction = Column(JSON, nullable=True)
    meal_ingredients = Column(JSON, nullable=True)

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, server_default="false")

    # Relationship to food item translations
    food_items = relationship(
        "FoodItemTranslationORM",
        back_populates="meal_translation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Relationship back to meal
    meal = relationship("MealORM", back_populates="translations")
