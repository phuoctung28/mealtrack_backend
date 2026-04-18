"""
Meal translation repository implementation.
Uses session factory pattern — each operation gets a fresh DB connection,
safe for use in long-lived singletons (e.g., event bus handlers).
"""
import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from src.domain.model.meal import MealTranslation
from src.domain.ports.meal_translation_repository_port import MealTranslationRepositoryPort
from src.infra.database.config import SessionLocal
from src.infra.database.models.meal.meal_translation_model import MealTranslationORM
from src.infra.database.models.meal.food_item_translation_model import FoodItemTranslationORM
from src.infra.mappers.meal_mapper import (
    meal_translation_orm_to_domain,
    meal_translation_domain_to_orm,
)

logger = logging.getLogger(__name__)


class MealTranslationRepository(MealTranslationRepositoryPort):
    """SQLAlchemy implementation of meal translation repository."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        """Initialize with session factory for fresh connections per operation."""
        self._session_factory = session_factory

    def save(self, translation: MealTranslation) -> MealTranslation:
        """Save a meal translation to the database."""
        db = self._session_factory()
        try:
            # Check for existing translation
            existing = (
                db.query(MealTranslationORM)
                .filter(MealTranslationORM.meal_id == translation.meal_id)
                .filter(MealTranslationORM.language == translation.language)
                .first()
            )

            if existing:
                # Update existing
                existing.dish_name = translation.dish_name
                existing.translated_at = translation.translated_at
                # Delete old food item translations and create new ones
                for fi in existing.food_items:
                    db.delete(fi)
                db.flush()

                for fi in translation.food_items:
                    db_fi = FoodItemTranslationORM(
                        meal_translation_id=existing.id,
                        food_item_id=fi.food_item_id,
                        name=fi.name,
                        description=fi.description,
                    )
                    db.add(db_fi)

                db.commit()
                db.refresh(existing)
                return meal_translation_orm_to_domain(existing)
            else:
                # Create new
                db_translation = meal_translation_domain_to_orm(translation)
                db.add(db_translation)
                db.commit()
                db.refresh(db_translation)
                return meal_translation_orm_to_domain(db_translation)

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save translation: {e}")
            raise
        finally:
            db.close()

    def get_by_meal_and_language(self, meal_id: str, language: str) -> Optional[MealTranslation]:
        """Get translation for a specific meal and language."""
        db = self._session_factory()
        try:
            db_translation = (
                db.query(MealTranslationORM)
                .filter(MealTranslationORM.meal_id == meal_id)
                .filter(MealTranslationORM.language == language)
                .first()
            )
            return meal_translation_orm_to_domain(db_translation) if db_translation else None
        finally:
            db.close()

    def delete_by_meal(self, meal_id: str) -> int:
        """Delete all translations for a meal."""
        db = self._session_factory()
        try:
            count = (
                db.query(MealTranslationORM)
                .filter(MealTranslationORM.meal_id == meal_id)
                .delete()
            )
            db.commit()
            return count
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
