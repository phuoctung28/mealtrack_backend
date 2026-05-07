"""
Drain the pending queue against real pgvector + real pending repo, with fakes for
embedding, image search, HTTP download, Cloudinary, and AI generators.
"""

import pytest
from unittest.mock import AsyncMock

from src.domain.model.meal_image_cache import PendingItem
from tests.fakes.fake_embedding_adapter import FakeEmbeddingAdapter
from src.infra.repositories.pending_meal_image_repository import (
    PendingMealImageRepository,
)
from src.infra.repositories.pgvector_meal_image_cache_repository import (
    PgvectorMealImageCacheRepository,
)


class _FakeImageSearch:
    async def fetch_candidates(self, name):
        return [{"url": "https://x/y.jpg", "thumbnail_url": None, "source": "pexels"}]


class _FakeHttp:
    async def download(self, url):
        return b"fakebytes"


class _FakeCloudinary:
    def save(self, data, content_type):
        return "https://cdn/final.jpg"


class _FakeAI:
    name = "pollinations"

    async def generate(self, prompt):
        return b"aibytes"


@pytest.mark.asyncio
async def test_drain_processes_pending_rows(db_session, monkeypatch):
    import importlib.util, os as _os

    _script = _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)),
        "..",
        "..",
        "..",
        "scripts",
        "resolve_pending_images.py",
    )
    _spec = importlib.util.spec_from_file_location(
        "resolve_pending_images", _os.path.abspath(_script)
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    drain = _mod.drain
    monkeypatch.setattr(
        "src.domain.services.meal_image_cache.resolve_meal_image_job.cosine_sim",
        lambda a, b: 0.95,
    )
    pending_repo = PendingMealImageRepository(db_session)
    cache_repo = PgvectorMealImageCacheRepository(db_session)

    await pending_repo.enqueue_many(
        [
            PendingItem(
                meal_name="Grilled Salmon",
                name_slug="grilled-salmon",
                candidate_image_url="https://pexels/salmon.jpg",
                candidate_source="pexels",
            ),
            PendingItem(
                meal_name="Pizza Margherita",
                name_slug="pizza-margherita",
                candidate_image_url="https://pexels/pizza.jpg",
                candidate_source="pexels",
            ),
        ]
    )

    await drain(
        pending_repo=pending_repo,
        cache_repo=cache_repo,
        embedder=FakeEmbeddingAdapter(),
        image_search=_FakeImageSearch(),
        http=_FakeHttp(),
        cloudinary=_FakeCloudinary(),
        ai_primary=_FakeAI(),
        ai_fallback=_FakeAI(),
        event_bus=AsyncMock(),
        image_threshold=0.85,
        max_jobs=50,
        inter_call_delay=0.0,
        max_attempts=5,
    )

    # Both pending rows should be gone
    remaining = await pending_repo.claim_batch(10)
    assert remaining == []

    # Both should be in the cache
    emb_salmon = (await FakeEmbeddingAdapter().embed_text(["Grilled Salmon"]))[0]
    hit = await cache_repo.query_nearest(emb_salmon)
    assert hit is not None
    assert hit.meal_name == "Grilled Salmon"
