import logging
import os
import uuid
from contextvars import ContextVar

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, sessionmaker, scoped_session

load_dotenv()

logger = logging.getLogger(__name__)

# Context variable to hold request-scoped session identifier
_request_id: ContextVar[str] = ContextVar("request_id", default=None)

SSL_ENABLED = os.getenv("DB_SSL_ENABLED", "true").lower() == "true"
SSL_VERIFY_CERT = os.getenv("DB_SSL_VERIFY_CERT", "false").lower() == "true"
SSL_VERIFY_IDENTITY = os.getenv("DB_SSL_VERIFY_IDENTITY", "false").lower() == "true"

logger.info(
    "SSL Configuration: enabled=%s, verify_cert=%s, verify_identity=%s",
    SSL_ENABLED,
    SSL_VERIFY_CERT,
    SSL_VERIFY_IDENTITY,
)

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    if SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
            "mysql://", "mysql+mysqlconnector://", 1
        )
    elif SQLALCHEMY_DATABASE_URL.startswith("mysql+pymysql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
            "mysql+pymysql://", "mysql+mysqlconnector://", 1
        )

    if SSL_ENABLED:
        ssl_params = [
            "ssl_disabled=false",
            f"ssl_verify_cert={str(SSL_VERIFY_CERT).lower()}",
            f"ssl_verify_identity={str(SSL_VERIFY_IDENTITY).lower()}",
            "ssl_ca=",
        ]

        if "?" in SQLALCHEMY_DATABASE_URL:
            SQLALCHEMY_DATABASE_URL += "&" + "&".join(ssl_params)
        else:
            SQLALCHEMY_DATABASE_URL += "?" + "&".join(ssl_params)

        masked_url = SQLALCHEMY_DATABASE_URL
        if "://" in masked_url and "@" in masked_url:
            protocol, remainder = masked_url.split("://", maxsplit=1)
            if ":" in remainder and "@" in remainder:
                auth_host = remainder.split("@")[0]
                if ":" in auth_host:
                    user = auth_host.split(":")[0]
                    masked_url = masked_url.replace(auth_host, f"{user}:***")
        logger.info("Final Database URL: %s", masked_url)
        logger.info("SSL Parameters added: %s", ssl_params)
else:
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "mealtrack")

    base_url = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    if SSL_ENABLED:
        ssl_params = [
            "ssl_disabled=false",
            f"ssl_verify_cert={str(SSL_VERIFY_CERT).lower()}",
            f"ssl_verify_identity={str(SSL_VERIFY_IDENTITY).lower()}",
            "ssl_ca=",
        ]
        SQLALCHEMY_DATABASE_URL = base_url + "?" + "&".join(ssl_params)
    else:
        SQLALCHEMY_DATABASE_URL = base_url

UVICORN_WORKERS = int(os.getenv("UVICORN_WORKERS", "4"))
POOL_SIZE_PER_WORKER = int(os.getenv("POOL_SIZE_PER_WORKER", "5"))
POOL_MAX_OVERFLOW = int(os.getenv("POOL_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", "300"))
POOL_ECHO = os.getenv("POOL_ECHO", "false").lower() == "true"

POOL_SIZE = max(1, UVICORN_WORKERS * POOL_SIZE_PER_WORKER)
TOTAL_POOL_CAPACITY = POOL_SIZE + POOL_MAX_OVERFLOW

logger.info(
    "Connection pool configuration -> workers: %s, pool_size: %s, "
    "max_overflow: %s, total_capacity: %s, timeout: %ss, recycle: %ss",
    UVICORN_WORKERS,
    POOL_SIZE,
    POOL_MAX_OVERFLOW,
    TOTAL_POOL_CAPACITY,
    POOL_TIMEOUT,
    POOL_RECYCLE,
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    echo_pool=POOL_ECHO,
    pool_pre_ping=True,
    pool_recycle=POOL_RECYCLE,
    pool_size=POOL_SIZE,
    max_overflow=POOL_MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    connect_args={
        "connection_timeout": 60,
        "charset": "utf8mb4",
        "autocommit": False,
        "ssl_disabled": not SSL_ENABLED,
        "ssl_verify_cert": SSL_VERIFY_CERT,
        "ssl_verify_identity": SSL_VERIFY_IDENTITY,
        "ssl_ca": "",
    },
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Scoped session - uses context var for request isolation
# This ensures each request gets its own session, even when using singleton services
ScopedSession = scoped_session(
    SessionLocal,
    scopefunc=lambda: _request_id.get()  # Scope based on request ID
)


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
        _request_id.reset(token) 