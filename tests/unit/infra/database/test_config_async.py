"""Unit tests for async database config."""
import pytest


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
