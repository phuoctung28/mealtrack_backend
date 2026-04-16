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

    http = AsyncMock()
    http.download.return_value = b"imgbytes"

    cloudinary = MagicMock()
    cloudinary.save.return_value = "https://cdn/final.jpg"

    ai_generator = AsyncMock()
    ai_generator.name = "cloudflare"
    ai_generator.generate.return_value = b"aibytes"

    event_bus = AsyncMock()

    return dict(
        cache=cache,
        text_embedder=text_embedder,
        image_scorer=image_scorer,
        http=http,
        cloudinary=cloudinary,
        ai_generator=ai_generator,
        event_bus=event_bus,
        image_threshold=0.85,
        cache_hit_threshold=0.80,
    )


@pytest.fixture
def job(deps):
    return ResolveMealImageJob(**deps)


@pytest.mark.asyncio
async def test_short_circuits_when_already_cached(job, deps):
    deps["cache"].query_nearest.return_value = CachedImage(
        meal_name="x", name_slug="x", image_url="u",
        thumbnail_url=None, source="pexels", confidence=0.9, cosine=0.999,
    )
    result = await job.run(_item_with_url())
    assert result.source == "pexels"
    deps["http"].download.assert_not_called()
    deps["cloudinary"].save.assert_not_called()


@pytest.mark.asyncio
async def test_uses_candidate_url_when_score_passes(job, deps):
    """Candidate URL passes threshold → stored, no AI call."""
    deps["image_scorer"].score_image_text.return_value = 0.92
    result = await job.run(_item_with_url())
    assert result.source == "pexels"
    assert result.image_url == "https://cdn/final.jpg"
    deps["http"].download.assert_awaited_once_with("https://pexels/a.jpg")
    deps["ai_generator"].generate.assert_not_called()
    deps["cache"].upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_falls_back_to_ai_when_candidate_score_too_low(job, deps):
    """Candidate URL fails threshold → AI generation."""
    deps["image_scorer"].score_image_text.return_value = 0.50
    result = await job.run(_item_with_url())
    assert result.source == "ai_generated"
    deps["ai_generator"].generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_goes_straight_to_ai_when_no_candidate_url(job, deps):
    """No candidate URL → web search already failed, skip to AI immediately."""
    result = await job.run(_item_without_url())
    assert result.source == "ai_generated"
    deps["http"].download.assert_not_called()
    deps["ai_generator"].generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_raises_when_ai_generator_fails(job, deps):
    deps["image_scorer"].score_image_text.return_value = 0.10
    deps["ai_generator"].generate.side_effect = RuntimeError("flux down")
    with pytest.raises(RuntimeError, match="AI image generation failed"):
        await job.run(_item_with_url())


@pytest.mark.asyncio
async def test_publishes_event_on_success(job, deps):
    deps["image_scorer"].score_image_text.return_value = 0.92
    await job.run(_item_with_url())
    deps["event_bus"].publish.assert_awaited_once()
    evt = deps["event_bus"].publish.await_args.args[0]
    assert evt.meal_name == "Grilled Salmon"
    assert evt.source == "pexels"
