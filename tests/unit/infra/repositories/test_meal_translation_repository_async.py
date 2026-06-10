from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.model.meal.meal_translation_domain_models import MealTranslation
from src.infra.repositories.meal_translation_repository_async import (
    AsyncMealTranslationRepository,
)


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows=None, rowcount=0):
        self._rows = rows or []
        self.rowcount = rowcount

    def scalars(self):
        return _Scalars(self._rows)


class _AsyncSession:
    def __init__(self, results):
        self._results = list(results)
        self.add = MagicMock()
        self.delete = AsyncMock()
        self.flush = AsyncMock()
        self.refresh = AsyncMock()

    async def execute(self, statement):
        return self._results.pop(0)


def _translation_orm():
    row = MagicMock()
    row.id = 12
    row.meal_id = "meal-1"
    row.language = "vi"
    row.dish_name = "Com ga"
    row.food_items = []
    row.translated_at = datetime(2026, 6, 9, tzinfo=UTC)
    row.meal_instruction = [{"instruction": "Cook", "duration_minutes": 5}]
    row.meal_ingredients = ["ga"]
    return row


def _translation_domain(dish_name="Com ga"):
    return MealTranslation(
        meal_id="meal-1",
        language="vi",
        dish_name=dish_name,
        food_items=[],
        translated_at=datetime(2026, 6, 9, tzinfo=UTC),
        meal_instruction=[{"instruction": "Cook", "duration_minutes": 5}],
        meal_ingredients=["ga"],
    )


def test_async_meal_translation_repository_satisfies_port_contract():
    assert AsyncMealTranslationRepository.__abstractmethods__ == frozenset()


@pytest.mark.asyncio
async def test_get_by_meal_and_language_maps_domain():
    session = _AsyncSession([_Result(rows=[_translation_orm()])])
    repo = AsyncMealTranslationRepository(session)

    result = await repo.get_by_meal_and_language("meal-1", "vi")

    assert result is not None
    assert result.meal_id == "meal-1"
    assert result.language == "vi"


@pytest.mark.asyncio
async def test_save_new_translation_flushes_without_committing():
    session = _AsyncSession([_Result(rows=[])])
    repo = AsyncMealTranslationRepository(session)

    result = await repo.save(_translation_domain())

    assert result.meal_id == "meal-1"
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once()
    assert not hasattr(session, "commit")


@pytest.mark.asyncio
async def test_delete_by_meal_flushes_and_returns_rowcount():
    session = _AsyncSession([_Result(rowcount=3)])
    repo = AsyncMealTranslationRepository(session)

    result = await repo.delete_by_meal("meal-1")

    assert result == 3
    session.flush.assert_awaited_once()
    assert not hasattr(session, "commit")
