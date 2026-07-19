from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.infra.repositories.meal_repository_async import AsyncMealRepository


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, rows):
        self.execute = AsyncMock(return_value=_Result(rows))


@pytest.mark.asyncio
async def test_aggregate_linked_ingredient_history_uses_grouped_projection():
    session = _Session(rows=[(11, date(2026, 7, 15), 500.0)])
    repo = AsyncMealRepository(session)

    buckets = await repo.aggregate_linked_ingredient_history(
        user_id="user-1",
        start_date=date(2026, 4, 17),
        end_date=date(2026, 7, 15),
        reference_date=date(2026, 7, 16),
        user_timezone="UTC",
    )

    statement = str(session.execute.await_args.args[0])
    assert "food_item.food_reference_id" in statement
    assert "least(food_item.quantity" in statement
    assert "GROUP BY food_item.food_reference_id" in statement
    assert "meal.user_id" in statement
    assert buckets[0].food_reference_id == 11
    assert buckets[0].age_days == 1
    assert buckets[0].capped_grams == 500.0
