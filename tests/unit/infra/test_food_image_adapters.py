"""Unit tests for Pexels/Unsplash food image adapters and the DI singleton."""
from unittest.mock import patch

import pytest

from src.api.dependencies import food_image as food_image_dep
from src.domain.services.meal_discovery.food_image_search_service import (
    FoodImageSearchService,
)
from src.infra.adapters.pexels_image_adapter import PexelsImageAdapter
from src.infra.adapters.unsplash_image_adapter import UnsplashImageAdapter


@pytest.mark.asyncio
class TestPexelsAdapter:
    async def test_returns_none_when_api_key_missing(self):
        with patch(
            "src.infra.adapters.pexels_image_adapter.settings"
        ) as mock_settings:
            mock_settings.PEXELS_API_KEY = None
            adapter = PexelsImageAdapter()
            result = await adapter.search("grilled chicken")
            assert result is None


@pytest.mark.asyncio
class TestUnsplashAdapter:
    async def test_returns_none_when_access_key_missing(self):
        with patch(
            "src.infra.adapters.unsplash_image_adapter.settings"
        ) as mock_settings:
            mock_settings.UNSPLASH_ACCESS_KEY = None
            adapter = UnsplashImageAdapter()
            result = await adapter.search("grilled chicken")
            assert result is None

    async def test_trigger_download_noop_when_key_missing(self):
        # Should return silently — no exception
        with patch(
            "src.infra.adapters.unsplash_image_adapter.settings"
        ) as mock_settings:
            mock_settings.UNSPLASH_ACCESS_KEY = None
            await UnsplashImageAdapter.trigger_download(
                "https://api.unsplash.com/photos/xyz/download"
            )

    async def test_trigger_download_noop_when_location_empty(self):
        with patch(
            "src.infra.adapters.unsplash_image_adapter.settings"
        ) as mock_settings:
            mock_settings.UNSPLASH_ACCESS_KEY = "test-key"
            await UnsplashImageAdapter.trigger_download("")


class TestFoodImageServiceSingleton:
    def setup_method(self):
        # Reset module-level singleton so each test starts fresh
        food_image_dep._instance = None

    def test_returns_service_with_pexels_then_unsplash_chain(self):
        service = food_image_dep.get_food_image_service()
        assert isinstance(service, FoodImageSearchService)
        assert len(service._adapters) == 2
        assert isinstance(service._adapters[0], PexelsImageAdapter)
        assert isinstance(service._adapters[1], UnsplashImageAdapter)

    def test_returns_same_instance_on_repeat_calls(self):
        first = food_image_dep.get_food_image_service()
        second = food_image_dep.get_food_image_service()
        assert first is second
