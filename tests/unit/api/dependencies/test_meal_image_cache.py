from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_meal_image_cache_service_returns_service():
    mock_session = MagicMock()

    with patch(
        "src.api.dependencies.meal_image_cache.AsyncPgvectorMealImageCacheRepository"
    ) as mock_repo, patch(
        "src.api.dependencies.meal_image_cache.get_openai_text_embedder"
    ) as mock_embedder, patch(
        "src.api.dependencies.meal_image_cache.get_settings"
    ) as mock_settings:
        mock_settings.return_value.OPENAI_API_KEY = "test-key"
        mock_settings.return_value.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.return_value.OPENAI_EMBEDDING_DIMENSIONS = 512
        mock_settings.return_value.TEXT_DEDUP_THRESHOLD = 0.85
        mock_embedder.return_value = MagicMock()
        mock_repo.return_value = MagicMock()

        from src.api.dependencies.meal_image_cache import get_meal_image_cache_service

        result = await get_meal_image_cache_service(session=mock_session)

        assert result is not None
        mock_repo.assert_called_once_with(mock_session)
        mock_embedder.assert_called_once_with("test-key", "text-embedding-3-small", 512)


@pytest.mark.asyncio
async def test_get_meal_image_cache_service_requires_openai_key():
    mock_session = MagicMock()

    with patch("src.api.dependencies.meal_image_cache.get_settings") as mock_settings:
        mock_settings.return_value.OPENAI_API_KEY = None

        from src.api.dependencies.meal_image_cache import get_meal_image_cache_service

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
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
