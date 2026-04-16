import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.model.meal_image_cache import CachedImage, PendingItem
from src.domain.services.meal_image_cache.resolve_meal_image_job import (
    ResolveMealImageJob,
)


def _item_with_url():
    return PendingItem(
        meal_name="Grilled Salmon",
        name_slug="grilled-salmon",
        candidate_image_url="https://pexels/a.jpg",
        candidate_thumbnail_url="https://pexels/t.jpg",
        candidate_source="pexels",
    )


def _item_without_url():
    return PendingItem(meal_name="Grilled Salmon", name_slug="grilled-salmon")


@pytest.fixture
def deps():
    cache = AsyncMock()
    cache.query_nearest.return_value = None

    text_embedder = AsyncMock()
    text_embedder.embed_text.return_value = [[0.0] * 768]

    image_scorer = AsyncMock()
    image_scorer.score_image_text.return_value = 0.92  # passes threshold by default

    image_search = AsyncMock()
    image_search.fetch_candidates.return_value = [
        {"url": "https://pexels/fallback.jpg", "thumbnail_url": None,
         "source": "pexels"},
    ]

    http = AsyncMock()
    http.download.return_value = b"imgbytes"

    cloudinary = MagicMock()
    cloudinary.save.return_value = "https://cdn/final.jpg"

    ai_generator = AsyncMock()
    ai_generator.name = "huggingface"
    ai_generator.generate.return_value = b"aibytes"

    event_bus = AsyncMock()

    return dict(
        cache=cache,
        text_embedder=text_embedder,
        image_scorer=image_scorer,
        image_search=image_search,
        http=http,
        cloudinary=cloudinary,
        ai_generator=ai_generator,
        event_bus=event_bus,
        image_threshold=0.85,
    )


@pytest.fixture
def job(deps):
    return ResolveMealImageJob(**deps)


@pytest.mark.asyncio
async def test_short_circuits_when_already_cached_exact(job, deps):
    deps["cache"].query_nearest.return_value = CachedImage(
        meal_name="x", name_slug="x", image_url="u",
        thumbnail_url=None, source="pexels", confidence=0.9, cosine=0.999,
    )
    result = await job.run(_item_with_url())
    assert result.source == "pexels"
    deps["image_search"].fetch_candidates.assert_not_called()
    deps["http"].download.assert_not_called()
    deps["cloudinary"].save.assert_not_called()


@pytest.mark.asyncio
async def test_reuses_candidate_url_without_calling_image_search(job, deps):
    """When the pending row has a URL, the job must NOT re-call FoodImageSearch."""
    deps["image_scorer"].score_image_text.return_value = 0.92
    result = await job.run(_item_with_url())
    assert result.source == "pexels"
    assert result.image_url == "https://cdn/final.jpg"
    deps["image_search"].fetch_candidates.assert_not_called()
    deps["http"].download.assert_awaited_once_with("https://pexels/a.jpg")
    deps["ai_generator"].generate.assert_not_called()
    deps["cache"].upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_falls_back_to_image_search_when_candidate_url_absent(job, deps):
    """Manual enqueue (no URL) → job fetches via FoodImageSearchService."""
    deps["image_scorer"].score_image_text.return_value = 0.92
    result = await job.run(_item_without_url())
    assert result.source == "pexels"
    deps["image_search"].fetch_candidates.assert_awaited_once_with("Grilled Salmon")
    deps["http"].download.assert_awaited_once_with("https://pexels/fallback.jpg")


@pytest.mark.asyncio
async def test_falls_back_to_ai_when_no_candidate_passes(job, deps):
    deps["image_scorer"].score_image_text.return_value = 0.50  # below threshold
    result = await job.run(_item_with_url())
    assert result.source == "ai_generated"
    deps["ai_generator"].generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_raises_when_generator_fails(job, deps):
    deps["image_scorer"].score_image_text.return_value = 0.10  # below threshold
    deps["ai_generator"].generate.side_effect = RuntimeError("sdxl down")
    with pytest.raises(RuntimeError):
        await job.run(_item_with_url())


@pytest.mark.asyncio
async def test_publishes_event_on_success(job, deps):
    deps["image_scorer"].score_image_text.return_value = 0.92
    await job.run(_item_with_url())
    deps["event_bus"].publish.assert_awaited_once()
    evt = deps["event_bus"].publish.await_args.args[0]
    assert evt.meal_name == "Grilled Salmon"
    assert evt.source == "pexels"
