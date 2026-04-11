"""
Meal translation database models.

Stores translated content separately from original English to support
multiple languages.
"""
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.domain.utils.timezone_utils import utc_now


class MealTranslation(Base):
    """
    Database model for meal translations.

    Stores translated dish_name for each language.
    """

    __tablename__ = 'meal_translation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(String(36), ForeignKey("meal.meal_id"), nullable=True, index=True)  # Nullable to prevent cascade delete
    language = Column(String(7), nullable=False)  # ISO 639-1: en, vi, es, fr, de, ja, zh
    dish_name = Column(String(255), nullable=False)
    translated_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)

    # DeepL-translated rich fields
    meal_instruction = Column(JSON, nullable=True)   # List[{instruction, duration_minutes}]
    meal_ingredients = Column(JSON, nullable=True)   # List[str] – ingredient names in order

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, server_default='false')

    # Relationship to food item translations
    food_items = relationship(
        "FoodItemTranslation",
        back_populates="meal_translation",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Relationship back to meal
    meal = relationship("Meal", back_populates="translations")

    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.meal import MealTranslation as DomainMealTranslation
        from src.domain.model.meal import FoodItemTranslation as DomainFoodItemTranslation

        return DomainMealTranslation(
            meal_id=self.meal_id,
            language=self.language,
            dish_name=self.dish_name,
            food_items=[
                DomainFoodItemTranslation(
                    food_item_id=fi.food_item_id,
                    name=fi.name,
                    description=fi.description
                )
                for fi in self.food_items
            ],
            translated_at=self.translated_at,
            meal_instruction=self.meal_instruction,
            meal_ingredients=self.meal_ingredients,
        )

    @classmethod
    def from_domain(cls, domain_model):
        """Create DB model from domain model."""
        from src.infra.database.models.meal.food_item_translation_model import FoodItemTranslation

        now = utc_now()

        translation = cls(
            meal_id=domain_model.meal_id,
            language=domain_model.language,
            dish_name=domain_model.dish_name,
            translated_at=domain_model.translated_at or now,
            created_at=now,
            meal_instruction=domain_model.meal_instruction,
            meal_ingredients=domain_model.meal_ingredients,
        )

        # Add food item translations
        for fi in domain_model.food_items:
            translation.food_items.append(
                FoodItemTranslation(
                    food_item_id=str(fi.food_item_id),
                    name=fi.name,
                    description=fi.description
                )
            )

        return translation
