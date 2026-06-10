"""Food-reference adapter backed by fresh async Unit of Work scopes."""

from __future__ import annotations

from typing import Any

from src.infra.database.uow_async import AsyncUnitOfWork


class AsyncFoodReferenceUowAdapter:
    """Expose food-reference repo methods without storing an AsyncSession."""

    def __init__(self, uow_factory: Any = AsyncUnitOfWork):
        self._uow_factory = uow_factory

    async def get_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        async with self._uow_factory() as uow:
            return await uow.food_references.get_by_barcode(barcode)

    async def get_by_id(self, ref_id: int) -> dict[str, Any] | None:
        async with self._uow_factory() as uow:
            return await uow.food_references.get_by_id(ref_id)

    async def get_by_fdc_id(self, fdc_id: int) -> dict[str, Any] | None:
        async with self._uow_factory() as uow:
            return await uow.food_references.get_by_fdc_id(fdc_id)

    async def search_by_name(
        self, query: str, region: str = "global", limit: int = 10
    ) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            return await uow.food_references.search_by_name(query, region, limit)

    async def find_batch_by_normalized_names(
        self, names_normalized: list[str]
    ) -> dict[str, dict[str, Any]]:
        async with self._uow_factory() as uow:
            return await uow.food_references.find_batch_by_normalized_names(
                names_normalized
            )

    async def find_by_normalized_name(
        self, name_normalized: str
    ) -> dict[str, Any] | None:
        async with self._uow_factory() as uow:
            return await uow.food_references.find_by_normalized_name(name_normalized)

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
        async with self._uow_factory() as uow:
            return await uow.food_references.upsert_by_normalized_name(
                name=name,
                name_normalized=name_normalized,
                protein_100g=protein_100g,
                carbs_100g=carbs_100g,
                fat_100g=fat_100g,
                fiber_100g=fiber_100g,
                sugar_100g=sugar_100g,
                source=source,
                is_verified=is_verified,
                external_id=external_id,
            )

    async def upsert(self, data: dict[str, Any]) -> None:
        async with self._uow_factory() as uow:
            await uow.food_references.upsert(data)
