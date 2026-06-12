from unittest.mock import AsyncMock

import pytest

from src.infra.repositories.meal_translation_uow_adapter import (
    AsyncMealTranslationUowAdapter,
)


class _Repo:
    def __init__(self):
        self.get_by_meal_and_language = AsyncMock(return_value="cached")
        self.save = AsyncMock(return_value="saved")


class _Uow:
    def __init__(self, repo: _Repo):
        self.meal_translations = repo
        self.exited = False

    async def __aenter__(self):
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
async def test_get_by_meal_and_language_uses_fresh_uow_scope():
    factory = _UowFactory()
    adapter = AsyncMealTranslationUowAdapter(factory)

    result = await adapter.get_by_meal_and_language("meal-1", "vi")

    assert result == "cached"
    factory.repo.get_by_meal_and_language.assert_awaited_once_with("meal-1", "vi")
    assert factory.instances[0].exited is True


@pytest.mark.asyncio
async def test_save_uses_fresh_uow_scope():
    factory = _UowFactory()
    adapter = AsyncMealTranslationUowAdapter(factory)

    result = await adapter.save("translation")

    assert result == "saved"
    factory.repo.save.assert_awaited_once_with("translation")
    assert factory.instances[0].exited is True
