from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services.nutrition_integrity_policy import NutritionIntegrityPolicy
from src.infra.repositories.food_reference_projection import (
    food_reference_model_to_dict,
)
from src.infra.repositories.food_reference_repository_async import (
    AsyncFoodReferenceRepository,
    _dedupe_search_projections,
)


class _Result:
    def __init__(self, rows=None):
        self._rows = rows or []

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _Session:
    def __init__(self, results):
        self.results = list(results)
        self.statements = []
        self.flush = AsyncMock()

    async def execute(self, statement):
        self.statements.append(statement)
        return self.results.pop(0)


def _row(food_id: int, *, source_namespace: str | None, source_food_id: str | None):
    row = MagicMock()
    row.id = food_id
    row.name = "Rice"
    row.name_normalized = "rice"
    row.brand = None
    row.source = "fatsecret"
    row.source_namespace = source_namespace
    row.source_food_id = source_food_id
    row.is_verified = True
    row.protein_100g = 2.7
    row.carbs_100g = 28.0
    row.fat_100g = 0.3
    row.fiber_100g = 0.4
    row.sugar_100g = 0.1
    row.serving_size = None
    row.serving_size_rows = []
    row.serving_sizes = [{"unit": "g", "gram_weight": 1}]
    row.nutrient_rows = []
    row.extra_nutrients = None
    return row


def test_projection_preserves_source_identity_and_filters_before_limit():
    invalid = _row(1, source_namespace="fatsecret", source_food_id="bad")
    invalid.protein_100g = 100
    invalid.carbs_100g = 100
    invalid.fat_100g = 100
    valid = _row(2, source_namespace="fatsecret", source_food_id="good")

    result = _dedupe_search_projections(
        [invalid, valid], 1, integrity_policy=NutritionIntegrityPolicy()
    )

    assert len(result) == 1
    assert result[0].id == 2
    assert result[0].source_namespace == "fatsecret"
    assert result[0].source_food_id == "good"


def test_model_dictionary_round_trips_legacy_unknown_and_provider_identity():
    row = _row(7, source_namespace="fatsecret", source_food_id="fs-7")
    projected = food_reference_model_to_dict(row)

    assert projected["source_namespace"] == "fatsecret"
    assert projected["source_food_id"] == "fs-7"

    legacy = _row(8, source_namespace=None, source_food_id=None)
    legacy_projected = food_reference_model_to_dict(legacy)
    assert legacy_projected["source_namespace"] is None
    assert legacy_projected["source_food_id"] is None


@pytest.mark.asyncio
async def test_search_local_overfetches_until_valid_rows_fill_requested_limit():
    invalid_rows = [
        _row(index, source_namespace="fatsecret", source_food_id=str(index))
        for index in range(10)
    ]
    for row in invalid_rows:
        row.protein_100g = 100
        row.carbs_100g = 100
        row.fat_100g = 100
    valid = _row(99, source_namespace="fatsecret", source_food_id="valid")
    session = _Session([_Result(invalid_rows), _Result([valid])])
    repo = AsyncFoodReferenceRepository(session)

    result = await repo.search_local("rice", "US", 1)

    assert [item.id for item in result] == [99]
    assert len(session.statements) == 2


@pytest.mark.asyncio
async def test_search_local_continues_after_bounded_batch_until_valid_row_is_found():
    invalid_rows = [
        _row(index, source_namespace="fatsecret", source_food_id=str(index))
        for index in range(300)
    ]
    for row in invalid_rows:
        row.protein_100g = 100
        row.carbs_100g = 100
        row.fat_100g = 100
    valid = _row(301, source_namespace="fatsecret", source_food_id="valid")
    session = _Session(
        [
            _Result(invalid_rows[:150]),
            _Result(invalid_rows[150:]),
            _Result([valid]),
        ]
    )
    repo = AsyncFoodReferenceRepository(session)

    result = await repo.search_local("rice", "US", 50)

    assert [item.id for item in result] == [301]
    assert len(session.statements) == 3


@pytest.mark.asyncio
async def test_upsert_persists_provider_namespace_and_opaque_id():
    refreshed = _row(7, source_namespace="fatsecret", source_food_id="fs-7")
    session = _Session([_Result(), _Result(), _Result(), _Result([refreshed])])
    repo = AsyncFoodReferenceRepository(session)

    result = await repo.upsert_by_normalized_name(
        name="Rice",
        name_normalized="rice",
        protein_100g=2.7,
        carbs_100g=28.0,
        fat_100g=0.3,
        fiber_100g=0.4,
        sugar_100g=0.1,
        source="fatsecret",
        is_verified=False,
        external_id="fs-7",
    )

    assert result["source_namespace"] == "fatsecret"
    assert result["source_food_id"] == "fs-7"
    assert "source_namespace" in str(session.statements[2])


@pytest.mark.asyncio
async def test_upsert_rejects_source_name_collision_for_review():
    legacy = _row(8, source_namespace=None, source_food_id=None)
    session = _Session([_Result(), _Result([legacy])])
    repo = AsyncFoodReferenceRepository(session)

    with pytest.raises(ValueError, match="collision requires review"):
        await repo.upsert_by_normalized_name(
            name="Rice",
            name_normalized="rice",
            protein_100g=2.7,
            carbs_100g=28.0,
            fat_100g=0.3,
            fiber_100g=0.4,
            sugar_100g=0.1,
            source="fatsecret",
            is_verified=False,
            external_id="fs-8",
        )


@pytest.mark.asyncio
async def test_upsert_rejects_provider_identity_rename_for_review():
    existing = _row(8, source_namespace="fatsecret", source_food_id="fs-8")
    session = _Session([_Result([existing]), _Result()])
    repo = AsyncFoodReferenceRepository(session)

    with pytest.raises(ValueError, match="collision requires review"):
        await repo.upsert_by_normalized_name(
            name="Brown Rice",
            name_normalized="brown rice",
            protein_100g=2.7,
            carbs_100g=28.0,
            fat_100g=0.3,
            fiber_100g=0.4,
            sugar_100g=0.1,
            source="fatsecret",
            is_verified=False,
            external_id="fs-8",
        )
