import logging
import os
import uuid
from contextvars import ContextVar

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, sessionmaker, scoped_session
from sqlalchemy.pool import NullPool, QueuePool

load_dotenv()

logger = logging.getLogger(__name__)

# Context variable to hold request-scoped session identifier
_request_id: ContextVar[str] = ContextVar("request_id", default=None)

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_DIRECT = os.getenv("DATABASE_URL_DIRECT")

if DATABASE_URL_DIRECT:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL_DIRECT
    DATABASE_URL_SOURCE = "DATABASE_URL_DIRECT"
elif DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    DATABASE_URL_SOURCE = "DATABASE_URL"
else:
    DATABASE_URL_SOURCE = "DB_*"
    db_user = os.getenv("DB_USER", "nutree")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "nutree")
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

# Normalise protocol — psycopg2 driver required for both pooler and direct URLs.
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql+psycopg2://", 1
    )
elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )

# Detect Neon pooler endpoint (PgBouncer) vs direct connection.
# Pooler URLs contain "-pooler" in the hostname.
# When using pooler: SQLAlchemy should NOT maintain its own pool (NullPool)
# because Neon's PgBouncer already handles connection reuse.
IS_NEON_POOLER = (
    DATABASE_URL_SOURCE != "DATABASE_URL_DIRECT"
    and "-pooler" in SQLALCHEMY_DATABASE_URL
)

# psycopg2 TCP keepalive — prevents idle connections from being silently dropped
# by firewalls/load balancers between app and Neon.
CONNECT_ARGS = {
    "connect_timeout": 10,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}

POOL_ECHO = os.getenv("POOL_ECHO", "false").lower() == "true"

if IS_NEON_POOLER:
    # Neon pooler (PgBouncer) handles connection reuse.
    # NullPool = each request opens a fresh connection to PgBouncer (cheap).
    POOL_SIZE = 0
    POOL_MAX_OVERFLOW = 0
    TOTAL_POOL_CAPACITY = 0

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,
        echo_pool=POOL_ECHO,
        poolclass=NullPool,
        connect_args=CONNECT_ARGS,
    )

    logger.info(
        "Database engine created with NullPool (Neon pooler detected, source=%s)",
        DATABASE_URL_SOURCE,
    )
else:
    # Direct connection or local PostgreSQL — use a small QueuePool.
    UVICORN_WORKERS = int(os.getenv("UVICORN_WORKERS", "4"))
    POOL_SIZE_PER_WORKER = int(os.getenv("POOL_SIZE_PER_WORKER", "3"))
    POOL_MAX_OVERFLOW = int(os.getenv("POOL_MAX_OVERFLOW", "2"))
    POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", "30"))
    POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", "120"))

    POOL_SIZE = max(1, UVICORN_WORKERS * POOL_SIZE_PER_WORKER)
    TOTAL_POOL_CAPACITY = POOL_SIZE + POOL_MAX_OVERFLOW

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,
        echo_pool=POOL_ECHO,
        poolclass=QueuePool,
        pool_recycle=POOL_RECYCLE,
        pool_size=POOL_SIZE,
        max_overflow=POOL_MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        connect_args=CONNECT_ARGS,
    )

    logger.info(
        "Database engine created with QueuePool -> source: %s, "
        "workers: %s, pool_size: %s, max_overflow: %s, "
        "total_capacity: %s, timeout: %ss, recycle: %ss",
        DATABASE_URL_SOURCE,
        UVICORN_WORKERS,
        POOL_SIZE,
        POOL_MAX_OVERFLOW,
        TOTAL_POOL_CAPACITY,
        POOL_TIMEOUT,
        POOL_RECYCLE,
    )

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Scoped session - uses context var for request isolation
# This ensures each request gets its own session, even when using singleton services
ScopedSession = scoped_session(SessionLocal, scopefunc=lambda: _request_id.get())


class Base(AsyncAttrs, DeclarativeBase):
    """Base declarative class with async attribute support."""


def get_db():
    """
    Dependency for FastAPI to get a database session.
    Uses scoped session for request isolation.

    This allows singleton services (like event bus) to safely access
    the current request's database session via ScopedSession().
    """
    # Set unique request ID for this scope
    request_id = str(uuid.uuid4())
    token = _request_id.set(request_id)

    try:
        db = ScopedSession()
        yield db
    finally:
        ScopedSession.remove()  # Clean up session for this scope
        try:
            _request_id.reset(token)
        except ValueError:
            # FastAPI runs sync generator cleanup in a different thread context
            # (via contextmanager_in_threadpool), so reset() may fail.
            # This is safe — ScopedSession.remove() already cleaned up the session,
            # and each request creates a fresh UUID regardless.
            pass
