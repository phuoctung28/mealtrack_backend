"""Unit tests for AsyncUnitOfWork."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_async_uow_commits_on_clean_exit():
    """Test that AsyncUnitOfWork commits on successful context exit."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("src.infra.database.uow_async.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value = mock_session
        from src.infra.database.uow_async import AsyncUnitOfWork

        async with AsyncUnitOfWork() as uow:
            assert uow.session is mock_session

    mock_session.commit.assert_awaited_once()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_uow_rolls_back_on_exception():
    """Test that AsyncUnitOfWork rolls back on exception."""
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.close = AsyncMock()

    with patch("src.infra.database.uow_async.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value = mock_session
        from src.infra.database.uow_async import AsyncUnitOfWork

        with pytest.raises(ValueError, match="boom"):
            async with AsyncUnitOfWork():
                raise ValueError("boom")

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
    mock_session.close.assert_awaited_once()
