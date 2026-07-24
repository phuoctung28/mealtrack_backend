"""PostgreSQL-backed catalog projection E2E tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.catalog_meal_seed_import_service import CatalogMealSeedImporter
from src.infra.repositories.catalog_recipe_repository_async import (
    AsyncCatalogMealRepository,
)
from src.infra.repositories.food_reference_repository_async import (
    AsyncFoodReferenceRepository,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_imported_catalog_meal_preserves_food_reference_and_derived_macros(
    pg_session: AsyncSession,
):
    food_repo = AsyncFoodReferenceRepository(pg_session)
    reference = await food_repo.upsert_by_normalized_name(
        name="Rice",
        name_normalized="rice",
        protein_100g=2.7,
        carbs_100g=28.0,
        fat_100g=0.3,
        fiber_100g=0.4,
        sugar_100g=0.1,
        source="catalog_seed",
        is_verified=True,
    )
    await pg_session.commit()
    assert reference is not None

    catalog_repo = AsyncCatalogMealRepository(pg_session)
    importer = CatalogMealSeedImporter(catalog_repo, food_repo)
    summary = await importer.import_manifest(
        {
            "recipes": [
                {
                    "recipe_key": "rice-breakfast",
                    "name": "Rice Breakfast",
                    "cuisine": "vietnamese",
                    "meal_types": ["breakfast"],
                    "ingredients": [
                        {
                            "food_reference_id": reference["id"],
                            "name": "Rice",
                            "quantity": 100,
                            "unit": "g",
                        }
                    ],
                }
            ]
        }
    )
    await pg_session.commit()

    meals = await catalog_repo.list_active_meals(meal_type="breakfast")

    assert summary.inserted == 1
    assert len(meals) == 1
    assert meals[0].ingredients[0].food_reference_id == reference["id"]
    assert float(meals[0].protein_g) == pytest.approx(2.7)
    assert float(meals[0].carbs_g) == pytest.approx(28.0)
    assert float(meals[0].fat_g) == pytest.approx(0.3)
    assert meals[0].calories == 125
