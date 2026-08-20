"""Unit tests for user meal scan caching."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
from src.app.handlers.command_handlers.scan_by_url_command_handler import (
    ScanByUrlCommandHandler,
)
from src.app.services.meal_scan_cache_service import (
    MealScanCacheService,
    content_fingerprint,
    scan_source_for_mode,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import Meal, MealImage, MealStatus
from src.domain.model.nutrition import Nutrition
from src.domain.model.nutrition.macros import Macros
from src.domain.parsers.vision_response_parser import VisionResponseParser

_IMAGE_URL = "https://res.cloudinary.com/test/image/upload/v1/mealtrack/food.jpg"
_PUBLIC_ID = "mealtrack/1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
_IMAGE_ID = "1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
_USER_ID = "00000000-0000-0000-0000-000000000001"


def _nutrition() -> Nutrition:
    return Nutrition(
        macros=Macros(protein=20, carbs=30, fat=5, fiber=2, sugar=1),
        food_items=[],
    )


def _ready_meal(*, meal_id: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") -> Meal:
    return Meal(
        meal_id=meal_id,
        user_id=_USER_ID,
        status=MealStatus.READY,
        created_at=datetime.now(timezone.utc),
        image=MealImage(
            image_id=_IMAGE_ID,
            format="jpeg",
            size_bytes=1024,
            url=_IMAGE_URL,
        ),
        source="scanner",
        dish_name="Cached Salad",
        ready_at=datetime.now(timezone.utc),
        nutrition=_nutrition(),
    )


def _make_uow(*, existing: Meal | None = None) -> MagicMock:
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.users = MagicMock()
    uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    uow.meals = MagicMock()
    saved_meals: list[Meal] = []

    async def capture_meal(meal):
        saved_meals.append(meal)
        return meal

    uow.meals.save = AsyncMock(side_effect=capture_meal)
    uow.meals.find_by_id = AsyncMock(
        side_effect=lambda mid, **kw: (
            existing
            if existing and existing.meal_id == mid
            else (saved_meals[-1] if saved_meals else None)
        )
    )
    uow.meals.find_ready_by_user_and_image_id = AsyncMock(return_value=existing)
    uow.commit = AsyncMock()
    uow._saved_meals = saved_meals
    return uow


def _install_fake_image_download(monkeypatch) -> None:
    from src.app.handlers.command_handlers import scan_by_url_command_handler as module

    class FakeResponse:
        def __init__(self, content: bytes):
            self.content = content

        def raise_for_status(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return FakeResponse(b"fake-image-bytes")

    monkeypatch.setattr(module.httpx, "AsyncClient", lambda timeout: FakeClient())
    monkeypatch.setattr(module, "compress_image", lambda raw_bytes: raw_bytes)


@pytest.mark.asyncio
async def test_scan_by_url_returns_cached_meal_without_vision(monkeypatch):
    _install_fake_image_download(monkeypatch)
    existing = _ready_meal()
    uow = _make_uow(existing=existing)
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    handler = ScanByUrlCommandHandler(
        uow=uow,
        event_bus=MagicMock(),
        vision_service=MagicMock(),
        gpt_parser=VisionResponseParser(),
        meal_value_insight_cache=cache,
    )
    handler.vision_service.analyze = AsyncMock()

    first = await handler.handle(
        ScanByUrlCommand(
            user_id=_USER_ID,
            image_url=_IMAGE_URL,
            public_id=_PUBLIC_ID,
        )
    )
    second = await handler.handle(
        ScanByUrlCommand(
            user_id=_USER_ID,
            image_url=_IMAGE_URL,
            public_id=_PUBLIC_ID,
        )
    )

    assert first.meal_id == existing.meal_id
    assert second.meal_id == existing.meal_id
    handler.vision_service.analyze.assert_not_awaited()
    uow.meals.save.assert_not_awaited()
    assert getattr(first, "_meal_scan_cache_hit", False) is True


@pytest.mark.asyncio
async def test_scan_by_url_remembers_meal_in_redis_after_create(monkeypatch):
    _install_fake_image_download(monkeypatch)
    uow = _make_uow()
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    handler = ScanByUrlCommandHandler(
        uow=uow,
        event_bus=MagicMock(),
        vision_service=MagicMock(),
        gpt_parser=VisionResponseParser(),
        meal_value_insight_cache=cache,
        cache_invalidation=MagicMock(after_meal_write=AsyncMock()),
    )
    handler.vision_service.analyze = AsyncMock(
        return_value={
            "structured_data": {
                "is_food": True,
                "dish_name": "Rice Bowl",
                "foods": [
                    {
                        "name": "Rice",
                        "quantity_g": 150,
                        "macros": {
                            "protein_g": 4,
                            "carbs_g": 40,
                            "fat_g": 1,
                            "fiber_g": 1,
                            "sugar_g": 0,
                        },
                    }
                ],
            }
        }
    )

    meal = await handler.handle(
        ScanByUrlCommand(
            user_id=_USER_ID,
            image_url=_IMAGE_URL,
            public_id=_PUBLIC_ID,
        )
    )

    key, ttl = CacheKeys.user_meal_scan(_USER_ID, _IMAGE_ID, "scanner")
    cache.set.assert_awaited()
    assert cache.set.await_args.args[0] == key
    assert cache.set.await_args.args[1] == meal.meal_id
    assert cache.set.await_args.args[2] == ttl


@pytest.mark.asyncio
async def test_scan_cache_service_redis_hit_loads_meal():
    existing = _ready_meal()
    uow = _make_uow(existing=existing)
    cache = MagicMock()
    cache.get = AsyncMock(return_value=existing.meal_id)
    cache.set = AsyncMock()
    service = MealScanCacheService(uow, cache)

    meal = await service.get_by_image_id(
        user_id=_USER_ID,
        image_id=_IMAGE_ID,
        source="scanner",
    )

    assert meal is not None
    assert meal.meal_id == existing.meal_id
    uow.meals.find_ready_by_user_and_image_id.assert_not_awaited()


def test_content_fingerprint_is_stable():
    assert content_fingerprint(b"abc") == content_fingerprint(b"abc")
    assert content_fingerprint(b"abc") != content_fingerprint(b"abd")


def test_scan_source_for_mode():
    assert scan_source_for_mode("scanner") == "scanner"
    assert scan_source_for_mode("food_label") == "food_label"
