import asyncio
import time
import pytest

from src.domain.model.meal_discovery.food_image import FoodImageResult


@pytest.mark.asyncio
async def test_image_fetch_runs_in_parallel():
    """Verify cache misses are fetched in parallel, not sequentially."""
    call_times = []

    async def mock_search(query: str):
        call_times.append(time.time())
        await asyncio.sleep(0.1)  # Simulate API latency
        return FoodImageResult(
            url=f"https://example.com/{query}.jpg",
            thumbnail_url=f"https://example.com/{query}_thumb.jpg",
            source="pexels",
            alt_text=query,
            photographer=None,
            photographer_url=None,
            download_location=None,
        )

    from src.api.routes.v1.meal_suggestions import _fetch_images_parallel

    names = ["meal1", "meal2", "meal3", "meal4"]
    results = await _fetch_images_parallel(names, mock_search, timeout=3.0)

    assert len(results) == 4
    assert all(r is not None for r in results)

    # All calls should start within 50ms of each other (parallel)
    spread = max(call_times) - min(call_times)
    assert spread < 0.05, f"Calls spread over {spread:.3f}s, should be parallel"


@pytest.mark.asyncio
async def test_parallel_fetch_isolates_failures():
    """Verify one failed fetch doesn't break others."""
    call_count = 0

    async def mock_search(query: str):
        nonlocal call_count
        call_count += 1
        if query == "fail_me":
            raise Exception("API error")
        return FoodImageResult(
            url=f"https://example.com/{query}.jpg",
            thumbnail_url=None,
            source="pexels",
            alt_text=query,
            photographer=None,
            photographer_url=None,
            download_location=None,
        )

    from src.api.routes.v1.meal_suggestions import _fetch_images_parallel

    names = ["good1", "fail_me", "good2"]
    results = await _fetch_images_parallel(names, mock_search, timeout=3.0)

    assert len(results) == 3
    assert results[0] is not None
    assert results[1] is None  # Failed fetch returns None
    assert results[2] is not None
    assert call_count == 3  # All were attempted
