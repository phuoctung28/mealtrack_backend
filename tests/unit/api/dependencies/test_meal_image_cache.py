from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_meal_image_cache_service_returns_service():
    mock_session = MagicMock()

    with patch(
        "src.api.dependencies.meal_image_cache.AsyncPgvectorMealImageCacheRepository"
    ) as mock_repo, patch(
        "src.api.dependencies.meal_image_cache.get_cloudflare_text_embedder"
    ) as mock_embedder, patch(
        "src.api.dependencies.meal_image_cache.get_settings"
    ) as mock_settings:
        mock_settings.return_value.CLOUDFLARE_ACCOUNT_ID = "acct"
        mock_settings.return_value.CLOUDFLARE_API_TOKEN = "token"
        mock_settings.return_value.CLOUDFLARE_WORKERS_AI_EMBEDDING_MODEL = (
            "@cf/google/embeddinggemma-300m"
        )
        mock_settings.return_value.CLOUDFLARE_WORKERS_AI_EMBEDDING_DIMENSIONS = 768
        mock_settings.return_value.CLOUDFLARE_WORKERS_AI_TIMEOUT_SECONDS = 60
        mock_settings.return_value.TEXT_DEDUP_THRESHOLD = 0.85
        mock_embedder.return_value = MagicMock()
        mock_repo.return_value = MagicMock()

        from src.api.dependencies.meal_image_cache import get_meal_image_cache_service

        result = await get_meal_image_cache_service(session=mock_session)

        assert result is not None
        mock_repo.assert_called_once_with(mock_session)
        mock_embedder.assert_called_once_with(
            "acct",
            "token",
            "@cf/google/embeddinggemma-300m",
            768,
            60,
        )


@pytest.mark.asyncio
async def test_get_meal_image_cache_service_requires_cloudflare_credentials():
    mock_session = MagicMock()

    with patch("src.api.dependencies.meal_image_cache.get_settings") as mock_settings:
        mock_settings.return_value.CLOUDFLARE_ACCOUNT_ID = ""
        mock_settings.return_value.CLOUDFLARE_API_TOKEN = ""

        from src.api.dependencies.meal_image_cache import get_meal_image_cache_service

        with pytest.raises(RuntimeError, match="CLOUDFLARE_ACCOUNT_ID"):
            await get_meal_image_cache_service(session=mock_session)


@pytest.mark.asyncio
async def test_get_pending_queue_returns_repository():
    mock_session = MagicMock()

    with patch(
        "src.api.dependencies.meal_image_cache.AsyncPendingMealImageRepository"
    ) as mock_repo:
        mock_repo.return_value = MagicMock()

        from src.api.dependencies.meal_image_cache import get_pending_queue

        result = await get_pending_queue(session=mock_session)

        assert result is not None
        mock_repo.assert_called_once_with(mock_session)
