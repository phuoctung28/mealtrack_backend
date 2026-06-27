"""Async food reference repository."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infra.database.models.food_reference_model import FoodReferenceModel
from src.infra.repositories.food_reference_projection import (
    FOOD_REFERENCE_SEED_COLUMNS,
    build_food_reference_nutrient_rows,
    build_food_reference_serving_rows,
    food_reference_model_to_dict,
)

logger = logging.getLogger(__name__)

_FOOD_REFERENCE_LOAD_OPTIONS = (
    selectinload(FoodReferenceModel.serving_size_rows),
    selectinload(FoodReferenceModel.nutrient_rows),
)


class AsyncFoodReferenceRepository:
    """Async repository for food reference CRUD operations."""

    _SEED_COLUMNS = FOOD_REFERENCE_SEED_COLUMNS

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        stmt = (
            select(FoodReferenceModel)
            .where(FoodReferenceModel.barcode == barcode)
            .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return food_reference_model_to_dict(model) if model else None

    async def get_by_id(self, ref_id: int) -> dict[str, Any] | None:
        stmt = (
            select(FoodReferenceModel)
            .where(FoodReferenceModel.id == ref_id)
            .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return food_reference_model_to_dict(model) if model else None

    async def get_by_fdc_id(self, fdc_id: int) -> dict[str, Any] | None:
        stmt = (
            select(FoodReferenceModel)
            .where(FoodReferenceModel.fdc_id == fdc_id)
            .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return food_reference_model_to_dict(model) if model else None

    async def search_by_name(
        self, query: str, region: str = "global", limit: int = 10
    ) -> list[dict[str, Any]]:
        stmt = (
            select(FoodReferenceModel)
            .where(FoodReferenceModel.name.ilike(f"%{query}%"))
            .where(FoodReferenceModel.region.in_([region, "global"]))
            .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [food_reference_model_to_dict(row) for row in result.scalars().all()]

    async def upsert(self, data: dict[str, Any]) -> None:
        """Insert or update a food reference by barcode without owning commit."""
        if data.get("barcode") and not data.get("is_verified", False):
            existing = await self._find_model_by_barcode(data["barcode"])
            if existing is not None and existing.is_verified:
                return

        values = {
            "barcode": data.get("barcode"),
            "name": data.get("name"),
            "name_vi": data.get("name_vi"),
            "brand": data.get("brand"),
            "protein_100g": data.get("protein_100g"),
            "carbs_100g": data.get("carbs_100g"),
            "fat_100g": data.get("fat_100g"),
            "fiber_100g": data.get("fiber_100g", 0),
            "sugar_100g": data.get("sugar_100g", 0),
            "serving_size": data.get("serving_size"),
            "serving_sizes": data.get("serving_sizes"),
            "image_url": data.get("image_url"),
            "source": data.get("source", "fatsecret"),
            "is_verified": data.get("is_verified", False),
            "fdc_id": data.get("fdc_id"),
            "category": data.get("category"),
            "region": data.get("region", "global"),
            "density": data.get("density", 1.0),
            "extra_nutrients": data.get("extra_nutrients"),
        }
        stmt = pg_insert(FoodReferenceModel).values(**values)
        update_fields = {k: v for k, v in values.items() if k != "barcode"}
        if not values["is_verified"]:
            update_fields.pop("is_verified", None)
        on_conflict_kwargs: dict[str, Any] = {
            "index_elements": [FoodReferenceModel.barcode],
            "set_": update_fields,
        }
        if not values["is_verified"]:
            on_conflict_kwargs["where"] = FoodReferenceModel.is_verified.is_(False)
        await self._session.execute(
            stmt.on_conflict_do_update(**on_conflict_kwargs)
        )
        await self._session.flush()

        refreshed = await self._find_after_upsert(values)
        if refreshed:
            await self._sync_normalized_children(refreshed, data)

    async def find_batch_by_normalized_names(
        self, names_normalized: list[str]
    ) -> dict[str, dict[str, Any]]:
        if not names_normalized:
            return {}

        stmt = (
            select(FoodReferenceModel)
            .where(FoodReferenceModel.name_normalized.in_(names_normalized))
            .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
        )
        result = await self._session.execute(stmt)
        return {
            row.name_normalized: food_reference_model_to_dict(row)
            for row in result.scalars().all()
            if row.name_normalized is not None
        }

    async def find_by_normalized_name(
        self, name_normalized: str
    ) -> dict[str, Any] | None:
        stmt = (
            select(FoodReferenceModel)
            .where(FoodReferenceModel.name_normalized == name_normalized)
            .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return food_reference_model_to_dict(model) if model else None

    async def upsert_by_normalized_name(
        self,
        name: str,
        name_normalized: str,
        protein_100g: float,
        carbs_100g: float,
        fat_100g: float,
        fiber_100g: float,
        sugar_100g: float,
        source: str,
        is_verified: bool,
        external_id: str | None = None,
    ) -> dict[str, Any] | None:
        existing = await self._find_model_by_normalized_name(name_normalized)
        if existing is not None and existing.is_verified and not is_verified:
            return food_reference_model_to_dict(existing)

        values = {
            "name": name,
            "name_normalized": name_normalized,
            "protein_100g": protein_100g,
            "carbs_100g": carbs_100g,
            "fat_100g": fat_100g,
            "fiber_100g": fiber_100g,
            "sugar_100g": sugar_100g,
            "source": source,
            "is_verified": is_verified,
            "region": "global",
        }
        update_fields = {k: v for k, v in values.items() if k != "name_normalized"}
        stmt = pg_insert(FoodReferenceModel).values(**values)
        on_conflict_kwargs: dict[str, Any] = {
            "index_elements": ["name_normalized"],
            "set_": update_fields,
        }
        if not is_verified:
            on_conflict_kwargs["where"] = FoodReferenceModel.is_verified.is_(False)
        await self._session.execute(stmt.on_conflict_do_update(**on_conflict_kwargs))
        await self._session.flush()

        refreshed = await self._find_model_by_normalized_name(name_normalized)
        return food_reference_model_to_dict(refreshed) if refreshed else None

    async def _find_model_by_normalized_name(
        self, name_normalized: str
    ) -> FoodReferenceModel | None:
        result = await self._session.execute(
            select(FoodReferenceModel)
            .where(FoodReferenceModel.name_normalized == name_normalized)
            .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
        )
        return result.scalars().first()

    async def _find_model_by_barcode(self, barcode: str) -> FoodReferenceModel | None:
        result = await self._session.execute(
            select(FoodReferenceModel)
            .where(FoodReferenceModel.barcode == barcode)
            .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
        )
        return result.scalars().first()

    async def _find_after_upsert(
        self,
        values: dict[str, Any],
    ) -> FoodReferenceModel | None:
        if values.get("barcode"):
            stmt = select(FoodReferenceModel).where(
                FoodReferenceModel.barcode == values["barcode"]
            )
        elif values.get("fdc_id"):
            stmt = select(FoodReferenceModel).where(
                FoodReferenceModel.fdc_id == values["fdc_id"]
            )
        else:
            return None
        result = await self._session.execute(stmt.options(*_FOOD_REFERENCE_LOAD_OPTIONS))
        return result.scalars().first()

    async def _sync_normalized_children(
        self,
        model: FoodReferenceModel,
        data: dict[str, Any],
    ) -> None:
        serving_sizes = data.get("serving_sizes")
        extra_nutrients = data.get("extra_nutrients")
        if serving_sizes is not None:
            model.serving_size_rows = build_food_reference_serving_rows(serving_sizes)
        if extra_nutrients is not None:
            model.nutrient_rows = build_food_reference_nutrient_rows(extra_nutrients)
        await self._session.flush()
