"""Unit tests for mealimage upsert / reload helpers on AsyncMealRepository."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.domain.model.meal import MealImage
from src.infra.repositories.meal_repository_async import AsyncMealRepository


@pytest.mark.asyncio
async def test_upsert_meal_image_updates_url_on_existing_row():
    repo = AsyncMealRepository(session=MagicMock())
    existing = SimpleNamespace(
        image_id="11111111-1111-1111-1111-111111111111",
        url=None,
        format="jpeg",
        size_bytes=1,
        width=None,
        height=None,
    )
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    repo.session.execute = AsyncMock(return_value=result)

    image = MealImage(
        image_id=existing.image_id,
        format="jpeg",
        size_bytes=4096,
        url="https://res.cloudinary.com/demo/image/upload/v1/mealtrack/abc.jpg",
    )

    saved = await repo._upsert_meal_image(image)

    assert saved is existing
    assert existing.url == image.url
    assert existing.size_bytes == 4096
    repo.session.add.assert_not_called()


@pytest.mark.asyncio
async def test_reload_meal_domain_falls_back_to_caller_image(monkeypatch):
    repo = AsyncMealRepository(session=MagicMock())
    meal_id = str(uuid4())
    mapped = MagicMock()
    mapped.image = None
    mapped.with_image = MagicMock(
        side_effect=lambda image: SimpleNamespace(image=image)
    )

    result = MagicMock()
    result.unique.return_value.scalars.return_value.first.return_value = object()
    repo.session.execute = AsyncMock(return_value=result)
    monkeypatch.setattr(
        "src.infra.repositories.meal_repository_async.meal_orm_to_domain",
        lambda _orm: mapped,
    )

    fallback = MealImage(
        image_id=str(uuid4()),
        format="jpeg",
        size_bytes=2048,
        url="https://res.cloudinary.com/demo/image/upload/v1/mealtrack/scan.jpg",
    )

    reloaded = await repo._reload_meal_domain(meal_id, fallback_image=fallback)

    assert reloaded.image is fallback
    mapped.with_image.assert_called_once_with(fallback)
