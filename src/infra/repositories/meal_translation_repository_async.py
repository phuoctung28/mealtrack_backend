"""Async meal translation repository."""

from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.model.meal import MealTranslation
from src.domain.ports.meal_translation_repository_port import (
    MealTranslationRepositoryPort,
)
from src.infra.database.models.meal.food_item_translation_model import (
    FoodItemTranslationORM,
)
from src.infra.database.models.meal.meal_translation_model import MealTranslationORM
from src.infra.mappers.meal_mapper import (
    meal_translation_domain_to_orm,
    meal_translation_orm_to_domain,
)

logger = logging.getLogger(__name__)


class AsyncMealTranslationRepository(MealTranslationRepositoryPort):
    """Async SQLAlchemy implementation of meal translation repository."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, translation: MealTranslation) -> MealTranslation:
        existing = await self._find_model(translation.meal_id, translation.language)
        if existing:
            existing.dish_name = translation.dish_name
            existing.translated_at = translation.translated_at
            existing.meal_instruction = translation.meal_instruction
            existing.meal_ingredients = translation.meal_ingredients
            for food_item in list(existing.food_items):
                await self._session.delete(food_item)
            await self._session.flush()

            for food_item in translation.food_items:
                self._session.add(
                    FoodItemTranslationORM(
                        meal_translation_id=existing.id,
                        food_item_id=str(food_item.food_item_id),
                        name=food_item.name,
                        description=food_item.description,
                    )
                )
            await self._session.flush()
            await self._session.refresh(existing)
            return meal_translation_orm_to_domain(existing)

        model = meal_translation_domain_to_orm(translation)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return meal_translation_orm_to_domain(model)

    async def get_by_meal_and_language(
        self, meal_id: str, language: str
    ) -> MealTranslation | None:
        model = await self._find_model(meal_id, language)
        return meal_translation_orm_to_domain(model) if model else None

    async def delete_by_meal(self, meal_id: str) -> int:
        result = await self._session.execute(
            delete(MealTranslationORM).where(MealTranslationORM.meal_id == meal_id)
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def _find_model(
        self, meal_id: str, language: str
    ) -> MealTranslationORM | None:
        result = await self._session.execute(
            select(MealTranslationORM)
            .where(MealTranslationORM.meal_id == meal_id)
            .where(MealTranslationORM.language == language)
            .options(selectinload(MealTranslationORM.food_items))
        )
        return result.scalars().first()
