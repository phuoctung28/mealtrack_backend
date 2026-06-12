"""Meal-translation adapter backed by fresh async Unit of Work scopes."""

from __future__ import annotations

from src.domain.model.meal import MealTranslation
from src.infra.database.uow_async import AsyncUnitOfWork


class AsyncMealTranslationUowAdapter:
    """Expose meal-translation repository methods without storing an AsyncSession."""

    def __init__(self, uow_factory=AsyncUnitOfWork):
        self._uow_factory = uow_factory

    async def get_by_meal_and_language(
        self, meal_id: str, language: str
    ) -> MealTranslation | None:
        async with self._uow_factory() as uow:
            return await uow.meal_translations.get_by_meal_and_language(
                meal_id, language
            )

    async def save(self, translation: MealTranslation) -> MealTranslation:
        async with self._uow_factory() as uow:
            return await uow.meal_translations.save(translation)
