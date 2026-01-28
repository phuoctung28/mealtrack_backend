"""
Food item translation database model.

See meal-translation-model.py for full implementation.
"""
from sqlalchemy import Column, String, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship

from src.infra.database.config import Base


class FoodItemTranslation(Base):
    """
    Database model for food item translations.

    Stores translated name and description for each food item.
    """

    __tablename__ = 'food_item_translation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_translation_id = Column(
        Integer,
        ForeignKey("meal_translation.id", ondelete="CASCADE"),
        nullable=False
    )
    food_item_id = Column(String(36), nullable=False, index=True)  # Reference only, no FK
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Relationship back to meal translation
    meal_translation = relationship("MealTranslation", back_populates="food_items")

    def to_domain(self):
        """Convert DB model to domain model."""
        from src.domain.model.meal import FoodItemTranslation as DomainFoodItemTranslation

        return DomainFoodItemTranslation(
            food_item_id=self.food_item_id,
            name=self.name,
            description=self.description
        )

    @classmethod
    def from_domain(cls, domain_model, meal_translation_id: int):
        """Create DB model from domain model."""
        return cls(
            meal_translation_id=meal_translation_id,
            food_item_id=domain_model.food_item_id,
            name=domain_model.name,
            description=domain_model.description
        )
