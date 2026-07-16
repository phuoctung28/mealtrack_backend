"""Async repository for immutable catalog recipe projections."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.model.meal_recommendation.catalog_recipe import (
    CatalogRecipeIngredient,
    CatalogRecipeVersion,
    CatalogRelease,
)
from src.domain.ports.catalog_recipe_repository_port import (
    CatalogRecipeRepositoryPort,
)
from src.infra.database.models.meal_recommendation import (
    CatalogRecipeIngredientORM,
    CatalogRecipeMealTypeORM,
    CatalogRecipeRightsRecordORM,
    CatalogRecipeVersionORM,
    CatalogReleaseORM,
)

_VERSION_LOAD_OPTIONS = (
    selectinload(CatalogRecipeVersionORM.recipe),
    selectinload(CatalogRecipeVersionORM.release),
    selectinload(CatalogRecipeVersionORM.meal_types),
    selectinload(CatalogRecipeVersionORM.ingredients),
    selectinload(CatalogRecipeVersionORM.rights_records),
)


class AsyncCatalogRecipeRepository(CatalogRecipeRepositoryPort):
    """Read-side repository for active catalog recipe versions."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_active_release(self) -> CatalogRelease | None:
        result = await self._session.execute(
            select(CatalogReleaseORM).where(CatalogReleaseORM.status == "active")
        )
        row = result.scalar_one_or_none()
        return _release_to_domain(row) if row else None

    async def list_active_versions(
        self,
        *,
        cuisine: str | None = None,
        meal_type: str | None = None,
    ) -> list[CatalogRecipeVersion]:
        stmt = (
            select(CatalogRecipeVersionORM)
            .join(CatalogRecipeVersionORM.release)
            .join(CatalogRecipeVersionORM.recipe)
            .where(CatalogReleaseORM.status == "active")
            .where(CatalogRecipeVersionORM.status == "published")
            .where(CatalogRecipeVersionORM.recipe.has(is_active=True))
            .options(*_VERSION_LOAD_OPTIONS)
            .order_by(CatalogRecipeVersionORM.name)
        )
        if cuisine is not None:
            stmt = stmt.where(CatalogRecipeVersionORM.recipe.has(cuisine=cuisine))
        if meal_type is not None:
            stmt = stmt.where(
                CatalogRecipeVersionORM.meal_types.any(
                    CatalogRecipeMealTypeORM.meal_type == meal_type
                )
            )

        result = await self._session.execute(stmt)
        rows = result.scalars().unique().all()
        return [_version_to_domain(row) for row in rows if _has_approved_rights(row)]

    async def get_version(self, version_id: str) -> CatalogRecipeVersion | None:
        stmt = (
            select(CatalogRecipeVersionORM)
            .join(CatalogRecipeVersionORM.release)
            .join(CatalogRecipeVersionORM.recipe)
            .where(CatalogRecipeVersionORM.id == version_id)
            .where(CatalogReleaseORM.status == "active")
            .where(CatalogRecipeVersionORM.status == "published")
            .where(CatalogRecipeVersionORM.recipe.has(is_active=True))
            .options(*_VERSION_LOAD_OPTIONS)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None or not _has_approved_rights(row):
            return None
        return _version_to_domain(row)


def _release_to_domain(row: CatalogReleaseORM) -> CatalogRelease:
    return CatalogRelease(
        id=cast(str, row.id),
        release_key=cast(str, row.release_key),
        manifest_digest=cast(str, row.manifest_digest),
        status=cast(str, row.status),
        expected_recipe_count=cast(int, row.expected_recipe_count),
        activated_at=cast(datetime | None, row.activated_at),
    )


def _version_to_domain(row: CatalogRecipeVersionORM) -> CatalogRecipeVersion:
    return CatalogRecipeVersion(
        id=cast(str, row.id),
        recipe_id=cast(str, row.recipe_id),
        release_id=cast(str, row.release_id),
        recipe_key=cast(str, row.recipe.recipe_key),
        name=cast(str, row.name),
        cuisine=cast(str, row.recipe.cuisine),
        status=cast(str, row.status),
        version_number=cast(int, row.version_number),
        calories=cast(int, row.calories),
        protein_g=cast(float, row.protein_g),
        carbs_g=cast(float, row.carbs_g),
        fat_g=cast(float, row.fat_g),
        fiber_g=cast(float, row.fiber_g),
        meal_types=tuple(item.meal_type for item in row.meal_types),
        ingredients=tuple(_ingredient_to_domain(item) for item in row.ingredients),
    )


def _ingredient_to_domain(row: CatalogRecipeIngredientORM) -> CatalogRecipeIngredient:
    return CatalogRecipeIngredient(
        food_reference_id=cast(int, row.food_reference_id),
        name=cast(str, row.name),
        quantity=cast(float, row.quantity),
        unit=cast(str, row.unit),
        resolved_grams=cast(float, row.resolved_grams),
        protein_g=cast(float, row.protein_g),
        carbs_g=cast(float, row.carbs_g),
        fat_g=cast(float, row.fat_g),
        fiber_g=cast(float, row.fiber_g),
        sugar_g=cast(float, row.sugar_g),
        position=cast(int, row.position),
        is_display_only=cast(bool, row.is_display_only),
    )


def _has_approved_rights(row: CatalogRecipeVersionORM) -> bool:
    return any(_is_approved_rights_record(record) for record in row.rights_records)


def _is_approved_rights_record(record: CatalogRecipeRightsRecordORM) -> bool:
    return cast(str, record.status) == "approved" and bool(record.agreement_identifier)
