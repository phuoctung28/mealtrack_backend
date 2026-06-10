from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infra.repositories.food_reference_repository_async import (
    AsyncFoodReferenceRepository,
)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        result = MagicMock()
        result.all.return_value = self._rows
        return result


class _AsyncSession:
    def __init__(self, rows):
        self.execute = AsyncMock(return_value=_Result(rows))


@pytest.mark.asyncio
async def test_find_batch_by_normalized_names_returns_dict():
    """Verify batch lookup returns dict keyed by normalized name."""
    row_1 = MagicMock()
    row_1.name_normalized = "chicken breast"
    row_1.protein_100g = 31.0
    row_1.id = 1

    row_2 = MagicMock()
    row_2.name_normalized = "rice"
    row_2.protein_100g = 2.7
    row_2.id = 2

    session = _AsyncSession([row_1, row_2])
    repo = AsyncFoodReferenceRepository(session)

    result = await repo.find_batch_by_normalized_names(
        ["chicken breast", "rice", "unknown"]
    )

    assert "chicken breast" in result
    assert "rice" in result
    assert "unknown" not in result
    assert result["chicken breast"]["protein_100g"] == 31.0


@pytest.mark.asyncio
async def test_find_batch_by_normalized_names_empty_input():
    """Verify empty input returns empty dict."""
    session = _AsyncSession([])
    repo = AsyncFoodReferenceRepository(session)
    result = await repo.find_batch_by_normalized_names([])

    assert result == {}
    session.execute.assert_not_awaited()
