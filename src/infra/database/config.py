"""
Sync SQLAlchemy engine for Alembic migrations and admin scripts.

This module is intentionally sync-only. The app runtime uses config_async.py.
Do NOT import this module from API routes, handlers, or repositories.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infra.database.base import Base  # noqa: F401 — re-exported for scripts

load_dotenv()

# URL priority: MIGRATION_DATABASE_URL > DATABASE_URL_DIRECT > DATABASE_URL
# Never use APP_DATABASE_URL here — that is the app runtime URL, not for migrations.
_raw_url = (
    os.getenv("MIGRATION_DATABASE_URL")
    or os.getenv("DATABASE_URL_DIRECT")
    or os.getenv("DATABASE_URL")
    or "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
        user=os.getenv("DB_USER", "nutree"),
        pw=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        db=os.getenv("DB_NAME", "nutree"),
    )
)

# Normalise to psycopg2 (sync driver)
SQLALCHEMY_DATABASE_URL = _raw_url
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
if "+asyncpg" in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("+asyncpg", "", 1)
if "+psycopg2" not in SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
