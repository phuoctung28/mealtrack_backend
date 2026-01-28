"""
Meal translation database models.

Stores translated content separately from original English to support
multiple languages.
"""
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import relationship

from src.infra.database.config import Base


class MealTranslation(Base):
    """
    Database model for meal translations.

    Stores translated dish_name for each language.
    """

    __tablename__ = 'meal_translation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(String(36), nullable=False, index=True)
    language = Column(String(7), nullable=False)  # ISO 639-1: en, vi, es, fr, de, ja, zh
    dish_name = Column(String(255), nullable=False)
    translated_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)

    # Relationship to food item translations
    food_items = relationship(
        "FoodItemTranslation",
        back_populates="meal_translation",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

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
            translated_at=self.translated_at
        )

    @classmethod
    def from_domain(cls, domain_model):
        """Create DB model from domain model."""
        from src.infra.database.models.meal.food_item_translation_model import FoodItemTranslation

        now = datetime.utcnow()

        translation = cls(
            meal_id=domain_model.meal_id,
            language=domain_model.language,
            dish_name=domain_model.dish_name,
            translated_at=domain_model.translated_at or now,
            created_at=now
        )

        # Add food item translations
        for fi in domain_model.food_items:
            translation.food_items.append(
                FoodItemTranslation(
                    food_item_id=fi.food_item_id,
                    name=fi.name,
                    description=fi.description
                )
            )

        return translation
