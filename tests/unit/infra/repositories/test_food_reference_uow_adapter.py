from unittest.mock import AsyncMock

import pytest

from src.infra.repositories.food_reference_uow_adapter import (
    AsyncFoodReferenceUowAdapter,
)


class _Repo:
    def __init__(self):
        self.get_by_barcode = AsyncMock(return_value={"barcode": "123"})
        self.find_batch_by_normalized_names = AsyncMock(return_value={"rice": {}})
        self.upsert_by_normalized_name = AsyncMock(return_value={"id": 7})
        self.upsert = AsyncMock(return_value=None)


class _Uow:
    def __init__(self, repo: _Repo):
        self.food_references = repo
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited = True
        return None


class _UowFactory:
    def __init__(self):
        self.repo = _Repo()
        self.instances: list[_Uow] = []

    def __call__(self):
        uow = _Uow(self.repo)
        self.instances.append(uow)
        return uow


@pytest.mark.asyncio
async def test_get_by_barcode_uses_fresh_uow_scope():
    factory = _UowFactory()
    adapter = AsyncFoodReferenceUowAdapter(factory)

    result = await adapter.get_by_barcode("123")

    assert result == {"barcode": "123"}
    factory.repo.get_by_barcode.assert_awaited_once_with("123")
    assert factory.instances[0].entered is True
    assert factory.instances[0].exited is True


@pytest.mark.asyncio
async def test_find_batch_by_normalized_names_uses_async_repo_method():
    factory = _UowFactory()
    adapter = AsyncFoodReferenceUowAdapter(factory)

    result = await adapter.find_batch_by_normalized_names(["rice"])

    assert result == {"rice": {}}
    factory.repo.find_batch_by_normalized_names.assert_awaited_once_with(["rice"])


@pytest.mark.asyncio
async def test_upsert_by_normalized_name_delegates_inside_uow_scope():
    factory = _UowFactory()
    adapter = AsyncFoodReferenceUowAdapter(factory)

    result = await adapter.upsert_by_normalized_name(
        name="Rice",
        name_normalized="rice",
        protein_100g=2.7,
        carbs_100g=28,
        fat_100g=0.3,
        fiber_100g=0.4,
        sugar_100g=0.1,
        source="fatsecret",
        is_verified=False,
    )

    assert result == {"id": 7}
    factory.repo.upsert_by_normalized_name.assert_awaited_once()
