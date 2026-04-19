"""Unit tests for AsyncUnitOfWork."""
import pytest
from unittest.mock import AsyncMock, patch

from src.infra.database.uow_async import AsyncUnitOfWork


@pytest.mark.asyncio
async def test_async_uow_commits_on_clean_exit():
    mock_session = AsyncMock()

    with patch("src.infra.database.uow_async.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value = mock_session
        async with AsyncUnitOfWork() as uow:
            pass

    mock_session.__aenter__.assert_not_awaited()
    mock_session.commit.assert_awaited_once()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_uow_rolls_back_on_exception():
    mock_session = AsyncMock()

    with patch("src.infra.database.uow_async.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value = mock_session
        with pytest.raises(ValueError):
            async with AsyncUnitOfWork():
                raise ValueError("boom")

    mock_session.__aenter__.assert_not_awaited()
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_uow_exposes_repos():
    mock_session = AsyncMock()

    with patch("src.infra.database.uow_async.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value = mock_session
        async with AsyncUnitOfWork() as uow:
            assert hasattr(uow, "meals")
            assert hasattr(uow, "users")
            assert hasattr(uow, "weekly_budgets")
            assert hasattr(uow, "cheat_days")
            assert hasattr(uow, "subscriptions")
            assert hasattr(uow, "notifications")
            assert hasattr(uow, "saved_suggestions")
