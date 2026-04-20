"""Unit tests for async database config."""
import pytest


@pytest.mark.asyncio
async def test_get_async_db_raises_clear_error_when_session_factory_missing(monkeypatch):
    import importlib
    import src.infra.database.config_async as cfg

    importlib.reload(cfg)
    monkeypatch.setattr(cfg, "AsyncSessionLocal", None)

    with pytest.raises(RuntimeError, match="AsyncSessionLocal is not initialized"):
        async for _ in cfg.get_async_db():
            pass


def test_async_url_rewrite_psycopg2_to_asyncpg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql+psycopg2://user:pw@host/db")
    import importlib
    import src.infra.database.config_async as cfg
    importlib.reload(cfg)
    assert "asyncpg" in cfg.ASYNC_DATABASE_URL
    assert "psycopg2" not in cfg.ASYNC_DATABASE_URL


def test_async_url_rewrite_plain_postgresql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql://user:pw@host/db")
    import importlib
    import src.infra.database.config_async as cfg
    importlib.reload(cfg)
    assert cfg.ASYNC_DATABASE_URL.startswith("postgresql+asyncpg://")


def test_async_url_rewrite_postgres_shorthand(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgres://user:pw@host/db")
    import importlib
    import src.infra.database.config_async as cfg
    importlib.reload(cfg)
    assert cfg.ASYNC_DATABASE_URL.startswith("postgresql+asyncpg://")
