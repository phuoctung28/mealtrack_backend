"""PostgreSQL-backed catalog seed import flow tests."""

from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.catalog_meal_seed_import_service import CatalogMealSeedImporter
from src.infra.database.models.meal_recommendation import MealCatalogORM
from src.infra.repositories.catalog_recipe_repository_async import (
    AsyncCatalogMealRepository,
)
from src.infra.repositories.food_reference_repository_async import (
    AsyncFoodReferenceRepository,
)

pytestmark = pytest.mark.integration


async def _seed_reference(session: AsyncSession, *, name: str = "Rice") -> int:
    repo = AsyncFoodReferenceRepository(session)
    result = await repo.upsert_by_normalized_name(
        name=name,
        name_normalized=name.lower(),
        protein_100g=2.7,
        carbs_100g=28.0,
        fat_100g=0.3,
        fiber_100g=0.4,
        sugar_100g=0.1,
        source="catalog_seed",
        is_verified=True,
    )
    await session.commit()
    assert result is not None
    return int(result["id"])


def _manifest(food_reference_id: int, *, key: str = "rice-breakfast") -> dict:
    return {
        "recipes": [
            {
                "recipe_key": key,
                "name": "Rice Breakfast",
                "cuisine": "vietnamese",
                "meal_types": ["breakfast"],
                "ingredients": [
                    {
                        "food_reference_id": food_reference_id,
                        "name": "Rice",
                        "quantity": 100,
                        "unit": "g",
                    }
                ],
            }
        ]
    }


async def _catalog_count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(MealCatalogORM))
    return int(result.scalar_one())


async def _import_manifest(session: AsyncSession, manifest: dict, *, dry_run=False):
    importer = CatalogMealSeedImporter(
        AsyncCatalogMealRepository(session),
        AsyncFoodReferenceRepository(session),
        dry_run=dry_run,
    )
    return await importer.import_manifest(manifest)


@pytest.mark.asyncio
async def test_catalog_import_dry_run_reports_without_writes(pg_session: AsyncSession):
    food_reference_id = await _seed_reference(pg_session)

    summary = await _import_manifest(
        pg_session,
        _manifest(food_reference_id),
        dry_run=True,
    )

    assert summary.inserted == 1
    assert await _catalog_count(pg_session) == 0


@pytest.mark.asyncio
async def test_catalog_import_replay_inserts_once(pg_session: AsyncSession):
    food_reference_id = await _seed_reference(pg_session)
    manifest = _manifest(food_reference_id)

    first = await _import_manifest(pg_session, manifest)
    await pg_session.commit()
    second = await _import_manifest(pg_session, manifest)

    assert first.inserted == 1
    assert second.inserted == 0
    assert second.skipped_existing == 1
    assert await _catalog_count(pg_session) == 1


@pytest.mark.asyncio
async def test_invalid_manifest_rolls_back_prepared_import(pg_session: AsyncSession):
    food_reference_id = await _seed_reference(pg_session)
    manifest = _manifest(food_reference_id)
    invalid = deepcopy(manifest["recipes"][0])
    invalid["recipe_key"] = "bad-row"
    invalid["ingredients"][0]["food_reference_id"] = 999_999
    manifest["recipes"].append(invalid)

    summary = await _import_manifest(pg_session, manifest)

    assert summary.errors
    assert summary.inserted == 0
    assert await _catalog_count(pg_session) == 0


@pytest.mark.asyncio
async def test_concurrent_catalog_import_serializes_to_one_insert(
    async_session_factory,
    pg_session: AsyncSession,
):
    food_reference_id = await _seed_reference(pg_session)
    manifest = _manifest(food_reference_id)

    async def run_import():
        async with async_session_factory() as session:
            summary = await _import_manifest(session, manifest)
            await session.commit()
            return summary

    first, second = await asyncio.gather(run_import(), run_import())

    assert sorted([first.inserted, second.inserted]) == [0, 1]
    assert sorted([first.skipped_existing, second.skipped_existing]) == [0, 1]
    assert await _catalog_count(pg_session) == 1


@pytest.mark.asyncio
async def test_near_duplicate_is_withheld_before_write(pg_session: AsyncSession):
    food_reference_id = await _seed_reference(pg_session)
    first = await _import_manifest(pg_session, _manifest(food_reference_id))
    await pg_session.commit()

    duplicate = _manifest(food_reference_id, key="rice-breakfast-copy")
    duplicate["recipes"][0]["ingredients"][0]["quantity"] = 101
    summary = await _import_manifest(pg_session, duplicate)

    assert first.inserted == 1
    assert summary.inserted == 0
    assert summary.review_required
    assert await _catalog_count(pg_session) == 1
