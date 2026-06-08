"""Unit tests for async database config."""

import pytest


@pytest.mark.asyncio
async def test_get_async_db_raises_clear_error_when_session_factory_missing(
    monkeypatch,
):
    import src.infra.database.config_async as cfg

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


def test_async_engine_defaults_to_null_pool_for_loop_safety(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql://user:pw@host/db")
    monkeypatch.delenv("ASYNC_DB_USE_QUEUE_POOL", raising=False)
    import importlib

    from sqlalchemy.pool import NullPool

    import src.infra.database.config_async as cfg

    importlib.reload(cfg)

    assert isinstance(cfg.async_engine.sync_engine.pool, NullPool)


def test_async_engine_queue_pool_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_DIRECT", "postgresql://user:pw@host/db")
    monkeypatch.setenv("ASYNC_DB_USE_QUEUE_POOL", "true")
    import importlib

    from sqlalchemy.pool import AsyncAdaptedQueuePool

    import src.infra.database.config_async as cfg

    importlib.reload(cfg)

    try:
        assert isinstance(cfg.async_engine.sync_engine.pool, AsyncAdaptedQueuePool)
    finally:
        monkeypatch.setenv("ASYNC_DB_USE_QUEUE_POOL", "false")
        importlib.reload(cfg)
