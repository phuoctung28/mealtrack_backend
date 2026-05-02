"""Async database engine, session factory, and FastAPI dependency."""

import logging
import os
from typing import Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

load_dotenv()

logger = logging.getLogger(__name__)


def _sanitize_asyncpg_url_and_connect_args(url: str) -> Tuple[str, dict]:
    """
    Remove libpq-only URL params that asyncpg cannot accept as connect kwargs.

    SQLAlchemy's URL query params are forwarded as driver kwargs, so we strip
    unsupported options and translate compatible ones into asyncpg connect_args.
    """
    try:
        parts = urlsplit(url)
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        sslmode: Optional[str] = None
        filtered: list[tuple[str, str]] = []
        connect_args: dict = {}
        for k, v in query_pairs:
            if k == "sslmode":
                sslmode = v
                continue
            if k == "channel_binding":
                # libpq option; asyncpg.connect() doesn't accept it.
                continue
            filtered.append((k, v))

        if sslmode and sslmode.lower() not in {"disable", "allow", "prefer"}:
            # asyncpg expects `ssl` instead of `sslmode`.
            connect_args["ssl"] = True

        if sslmode is None and len(filtered) == len(query_pairs):
            return url, connect_args

        new_query = urlencode(filtered)
        sanitized = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
        )
        return sanitized, connect_args
    except Exception:  # noqa: BLE001
        # If parsing fails, keep original URL; engine init will surface any issues.
        return url, {}


_raw_url = (
    os.getenv("DATABASE_URL_DIRECT")
    or os.getenv("DATABASE_URL")
    or "postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}".format(
        user=os.getenv("DB_USER", "nutree"),
        pw=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        db=os.getenv("DB_NAME", "nutree"),
    )
)

# Normalise driver to asyncpg
if _raw_url.startswith("postgres://"):
    ASYNC_DATABASE_URL = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql://") and "+asyncpg" not in _raw_url:
    ASYNC_DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql+psycopg2://"):
    ASYNC_DATABASE_URL = _raw_url.replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://", 1
    )
else:
    ASYNC_DATABASE_URL = _raw_url

# Render/Neon style URLs may include libpq params (sslmode/channel_binding),
# which must be translated/removed for asyncpg.
ASYNC_DATABASE_URL, _connect_args = _sanitize_asyncpg_url_and_connect_args(
    ASYNC_DATABASE_URL
)

# Detect Neon pooler — use NullPool (PgBouncer manages connections)
_IS_NEON_POOLER = (
    "-pooler" in ASYNC_DATABASE_URL and os.getenv("DATABASE_URL_DIRECT") is None
)

_UVICORN_WORKERS = int(os.getenv("UVICORN_WORKERS", "4"))
_ASYNC_POOL_SIZE = int(os.getenv("ASYNC_POOL_SIZE_PER_WORKER", "3"))
_ASYNC_POOL_OVERFLOW = int(os.getenv("ASYNC_POOL_MAX_OVERFLOW", "2"))
_ASYNC_POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", "10"))

try:
    if _IS_NEON_POOLER:
        async_engine = create_async_engine(
            ASYNC_DATABASE_URL,
            echo=False,
            poolclass=NullPool,
            connect_args=_connect_args,
        )
        logger.info("Async engine: NullPool (Neon pooler detected)")
    else:
        async_engine = create_async_engine(
            ASYNC_DATABASE_URL,
            echo=False,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=_UVICORN_WORKERS * _ASYNC_POOL_SIZE,
            max_overflow=_ASYNC_POOL_OVERFLOW,
            pool_recycle=120,
            pool_timeout=_ASYNC_POOL_TIMEOUT,
            connect_args=_connect_args,
        )
        logger.info(
            "Async engine: AsyncAdaptedQueuePool pool_size=%s max_overflow=%s",
            _UVICORN_WORKERS * _ASYNC_POOL_SIZE,
            _ASYNC_POOL_OVERFLOW,
        )

    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
except Exception as _engine_init_error:  # noqa: BLE001
    # asyncpg not installed (e.g. unit-test environment without the driver).
    # Defer the error to first actual database use so imports succeed.
    logger.warning(
        "Async engine could not be initialised at import time (%s); "
        "any attempt to open an AsyncUnitOfWork will raise.",
        _engine_init_error,
    )
    async_engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]


async def get_async_db():
    """FastAPI dependency: yields an AsyncSession, closes after request."""
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "AsyncSessionLocal is not initialized. Async engine setup failed; "
            "check async DB configuration."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
