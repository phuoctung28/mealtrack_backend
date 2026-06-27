from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infra.repositories.food_reference_repository_async import (
    AsyncFoodReferenceRepository,
)


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows=None, one=None):
        self._rows = rows or []
        self._one = one

    def scalars(self):
        return _Scalars(self._rows)

    def scalar_one_or_none(self):
        return self._one


class _AsyncSession:
    def __init__(self, results):
        self._results = list(results)
        self.statement = None
        self.flush = AsyncMock()

    async def execute(self, statement):
        self.statement = statement
        return self._results.pop(0)


def _food_row(name_normalized="rice", verified=False):
    row = MagicMock()
    row.id = 7
    row.barcode = None
    row.name = "Rice"
    row.name_vi = None
    row.brand = None
    row.category = None
    row.region = "global"
    row.fdc_id = None
    row.protein_100g = 2.7
    row.carbs_100g = 28.0
    row.fat_100g = 0.3
    row.fiber_100g = 0.4
    row.sugar_100g = 0.1
    row.serving_size_rows = []
    row.serving_sizes = None
    row.density = 1.0
    row.serving_size = None
    row.nutrient_rows = []
    row.extra_nutrients = None
    row.source = "seed"
    row.is_verified = verified
    row.image_url = None
    row.name_normalized = name_normalized
    return row


async def _upsert_default(repo: AsyncFoodReferenceRepository, **overrides):
    values = {
        "name": "Rice",
        "name_normalized": "rice",
        "protein_100g": 1,
        "carbs_100g": 2,
        "fat_100g": 3,
        "fiber_100g": 0,
        "sugar_100g": 0,
        "source": "fatsecret",
        "is_verified": False,
    }
    values.update(overrides)
    return await repo.upsert_by_normalized_name(**values)


@pytest.mark.asyncio
async def test_find_batch_by_normalized_names_returns_dict_by_normalized_name():
    row = _food_row()
    session = _AsyncSession([_Result(rows=[row])])
    repo = AsyncFoodReferenceRepository(session)

    result = await repo.find_batch_by_normalized_names(["rice"])

    assert result["rice"]["id"] == 7
    assert "food_reference.name_normalized" in str(session.statement)


@pytest.mark.asyncio
async def test_find_batch_by_normalized_names_returns_empty_dict_for_empty_input():
    session = _AsyncSession([])
    repo = AsyncFoodReferenceRepository(session)

    assert await repo.find_batch_by_normalized_names([]) == {}
    assert session.statement is None


@pytest.mark.asyncio
async def test_find_by_normalized_name_uses_scalars_first():
    row = _food_row()
    result = MagicMock()
    result.scalars.return_value.first.return_value = row
    session = _AsyncSession([result])
    repo = AsyncFoodReferenceRepository(session)

    found = await repo.find_by_normalized_name("rice")

    result.scalars.assert_called_once()
    result.scalars.return_value.first.assert_called_once()
    assert found is not None
    assert found["id"] == 7


@pytest.mark.asyncio
async def test_upsert_by_normalized_name_preserves_verified_row_without_flush():
    row = _food_row(verified=True)
    session = _AsyncSession([_Result(rows=[row])])
    repo = AsyncFoodReferenceRepository(session)

    result = await _upsert_default(repo)

    assert result["id"] == 7
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_upsert_by_normalized_name_flushes_without_committing():
    row = _food_row()
    session = _AsyncSession([_Result(rows=[]), _Result(), _Result(rows=[row])])
    repo = AsyncFoodReferenceRepository(session)

    result = await _upsert_default(repo)

    assert result["id"] == 7
    session.flush.assert_awaited_once()
    assert not hasattr(session, "commit")


@pytest.mark.asyncio
async def test_upsert_by_normalized_name_uses_on_conflict_do_update():
    row = _food_row()
    session = _AsyncSession([_Result(rows=[]), _Result(), _Result(rows=[row])])
    repo = AsyncFoodReferenceRepository(session)
    statement = MagicMock()
    statement.values.return_value = statement
    statement.on_conflict_do_update.return_value = statement

    with patch(
        "src.infra.repositories.food_reference_repository_async.pg_insert",
        return_value=statement,
    ):
        await _upsert_default(repo)

    statement.values.assert_called_once()
    statement.on_conflict_do_update.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_by_normalized_name_verified_protection_skips_upsert():
    row = _food_row(verified=True)
    session = _AsyncSession([_Result(rows=[row])])
    repo = AsyncFoodReferenceRepository(session)

    with patch(
        "src.infra.repositories.food_reference_repository_async.pg_insert"
    ) as insert:
        result = await _upsert_default(repo, protein_100g=99)

    insert.assert_not_called()
    session.flush.assert_not_awaited()
    assert result is not None
    assert result["protein_100g"] == pytest.approx(2.7)


@pytest.mark.asyncio
async def test_upsert_by_barcode_uses_on_conflict_and_flushes_children():
    row = _food_row()
    row.barcode = "123"
    session = _AsyncSession([_Result(rows=[]), _Result(), _Result(rows=[row])])
    repo = AsyncFoodReferenceRepository(session)
    statement = MagicMock()
    statement.values.return_value = statement
    statement.on_conflict_do_update.return_value = statement

    with patch(
        "src.infra.repositories.food_reference_repository_async.pg_insert",
        return_value=statement,
    ):
        await repo.upsert(
            {
                "barcode": "123",
                "name": "Rice",
                "protein_100g": 2.7,
                "carbs_100g": 28,
                "fat_100g": 0.3,
                "serving_sizes": [{"name": "cup", "grams": 158}],
                "extra_nutrients": {"sodium_mg": 1},
            }
        )

    statement.values.assert_called_once()
    statement.on_conflict_do_update.assert_called_once()
    assert session.flush.await_count == 2
    assert row.serving_size_rows
    assert row.nutrient_rows


@pytest.mark.asyncio
async def test_upsert_by_barcode_persists_verified_flag():
    row = _food_row()
    row.barcode = "00036000291452"
    session = _AsyncSession([_Result(), _Result(rows=[row])])
    repo = AsyncFoodReferenceRepository(session)
    statement = MagicMock()
    statement.values.return_value = statement
    statement.on_conflict_do_update.return_value = statement

    with patch(
        "src.infra.repositories.food_reference_repository_async.pg_insert",
        return_value=statement,
    ):
        await repo.upsert(
            {
                "barcode": "00036000291452",
                "name": "Cereal",
                "protein_100g": 8,
                "carbs_100g": 72,
                "fat_100g": 2.5,
                "source": "usda_fdc",
                "is_verified": True,
            }
        )

    values = statement.values.call_args.kwargs
    assert values["is_verified"] is True
    statement.on_conflict_do_update.assert_called_once()
    assert "where" not in statement.on_conflict_do_update.call_args.kwargs


@pytest.mark.asyncio
async def test_unverified_barcode_upsert_does_not_sync_children_on_verified_row():
    row = _food_row(verified=True)
    row.barcode = "00036000291452"
    session = _AsyncSession([_Result(rows=[row])])
    repo = AsyncFoodReferenceRepository(session)

    with patch(
        "src.infra.repositories.food_reference_repository_async.pg_insert"
    ) as insert:
        await repo.upsert(
            {
                "barcode": "00036000291452",
                "name": "Unverified",
                "protein_100g": 1,
                "carbs_100g": 2,
                "fat_100g": 3,
                "source": "brave_search",
                "is_verified": False,
                "serving_sizes": [{"name": "cup", "grams": 100}],
                "extra_nutrients": {"sodium_mg": 1},
            }
        )

    insert.assert_not_called()
    assert row.serving_size_rows == []
    assert row.nutrient_rows == []
    session.flush.assert_not_awaited()
