from unittest.mock import MagicMock

import pytest

from src.infra.repositories.catalog_recipe_repository_async import (
    AsyncCatalogRecipeRepository,
)


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def unique(self):
        return self

    def all(self):
        return self._rows


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

    async def execute(self, statement):
        self.statement = statement
        return self._results.pop(0)


def _release_row():
    row = MagicMock()
    row.id = "release-1"
    row.release_key = "2026-q3"
    row.manifest_digest = "a" * 64
    row.status = "active"
    row.expected_recipe_count = 180
    row.activated_at = None
    return row


def _version_row(*, rights_status="approved"):
    recipe = MagicMock()
    recipe.recipe_key = "vn-rice"
    recipe.cuisine = "vietnamese"
    recipe.is_active = True

    meal_type = MagicMock()
    meal_type.meal_type = "breakfast"

    ingredient = MagicMock()
    ingredient.food_reference_id = 7
    ingredient.name = "Rice"
    ingredient.quantity = 100
    ingredient.unit = "g"
    ingredient.resolved_grams = 100
    ingredient.protein_g = 2.7
    ingredient.carbs_g = 28.0
    ingredient.fat_g = 0.3
    ingredient.fiber_g = 0.4
    ingredient.sugar_g = 0.1
    ingredient.position = 0
    ingredient.is_display_only = False

    rights = MagicMock()
    rights.status = rights_status
    rights.agreement_identifier = "agreement-1"

    row = MagicMock()
    row.id = "version-1"
    row.recipe_id = "recipe-1"
    row.release_id = "release-1"
    row.recipe = recipe
    row.name = "Rice Bowl"
    row.status = "published"
    row.version_number = 1
    row.calories = 126
    row.protein_g = 2.7
    row.carbs_g = 28.0
    row.fat_g = 0.3
    row.fiber_g = 0.4
    row.meal_types = [meal_type]
    row.ingredients = [ingredient]
    row.rights_records = [rights]
    return row


@pytest.mark.asyncio
async def test_get_active_release_returns_typed_projection():
    session = _AsyncSession([_Result(one=_release_row())])
    repo = AsyncCatalogRecipeRepository(session)

    result = await repo.get_active_release()

    assert result is not None
    assert result.release_key == "2026-q3"
    assert result.expected_recipe_count == 180
    assert "catalog_releases.status" in str(session.statement)


@pytest.mark.asyncio
async def test_list_active_versions_filters_to_approved_rights():
    session = _AsyncSession(
        [_Result(rows=[_version_row(), _version_row(rights_status="pending")])]
    )
    repo = AsyncCatalogRecipeRepository(session)

    result = await repo.list_active_versions(
        cuisine="vietnamese",
        meal_type="breakfast",
    )

    assert len(result) == 1
    assert result[0].recipe_key == "vn-rice"
    assert result[0].meal_types == ("breakfast",)
    assert result[0].ingredients[0].food_reference_id == 7
    assert "catalog_recipe_versions.status" in str(session.statement)
    assert "catalog_releases.status" in str(session.statement)


@pytest.mark.asyncio
async def test_get_version_rejects_missing_approved_rights():
    session = _AsyncSession([_Result(one=_version_row(rights_status="pending"))])
    repo = AsyncCatalogRecipeRepository(session)

    assert await repo.get_version("version-1") is None
    assert "catalog_releases.status" in str(session.statement)


@pytest.mark.asyncio
async def test_get_version_scopes_to_active_release():
    session = _AsyncSession([_Result(one=_version_row())])
    repo = AsyncCatalogRecipeRepository(session)

    result = await repo.get_version("version-1")

    assert result is not None
    assert result.id == "version-1"
    assert "catalog_releases.status" in str(session.statement)
