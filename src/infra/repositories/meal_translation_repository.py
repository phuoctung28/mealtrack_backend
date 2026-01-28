"""
Meal translation repository implementation.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.domain.model.meal import MealTranslation
from src.domain.ports.meal_translation_repository_port import MealTranslationRepositoryPort
from src.infra.database.models.meal.meal_translation_model import MealTranslation as DBMealTranslation

logger = logging.getLogger(__name__)


class MealTranslationRepository(MealTranslationRepositoryPort):
    """SQLAlchemy implementation of meal translation repository."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def save(self, translation: MealTranslation) -> MealTranslation:
        """Save a meal translation to the database."""
        try:
            # Check for existing translation
            existing = (
                self.db.query(DBMealTranslation)
                .filter(DBMealTranslation.meal_id == translation.meal_id)
                .filter(DBMealTranslation.language == translation.language)
                .first()
            )

            if existing:
                # Update existing
                existing.dish_name = translation.dish_name
                existing.translated_at = translation.translated_at
                # Delete old food item translations and create new ones
                for fi in existing.food_items:
                    self.db.delete(fi)
                self.db.flush()

                for fi in translation.food_items:
                    from src.infra.database.models.meal.food_item_translation_model import FoodItemTranslation
                    db_fi = FoodItemTranslation(
                        meal_translation_id=existing.id,
                        food_item_id=fi.food_item_id,
                        name=fi.name,
                        description=fi.description
                    )
                    self.db.add(db_fi)

                self.db.commit()
                self.db.refresh(existing)
                return existing.to_domain()
            else:
                # Create new
                db_translation = DBMealTranslation.from_domain(translation)
                self.db.add(db_translation)
                self.db.commit()
                self.db.refresh(db_translation)
                return db_translation.to_domain()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save translation: {e}")
            raise

    def get_by_meal_and_language(self, meal_id: str, language: str) -> Optional[MealTranslation]:
        """Get translation for a specific meal and language."""
        db_translation = (
            self.db.query(DBMealTranslation)
            .filter(DBMealTranslation.meal_id == meal_id)
            .filter(DBMealTranslation.language == language)
            .first()
        )
        return db_translation.to_domain() if db_translation else None

    def delete_by_meal(self, meal_id: str) -> int:
        """Delete all translations for a meal."""
        count = (
            self.db.query(DBMealTranslation)
            .filter(DBMealTranslation.meal_id == meal_id)
            .delete()
        )
        self.db.commit()
        return count
