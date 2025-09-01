"""
Test database configuration using SQLite in-memory for fast, isolated testing.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infra.database.config import Base


def get_test_database_url() -> str:
    """Get database URL for testing."""
    # Always use in-memory SQLite for maximum speed and isolation
    return "sqlite:///:memory:"


def create_test_engine():
    """Create test database engine with SQLite in-memory configuration."""
    database_url = get_test_database_url()
    
    # SQLite in-memory configuration - always safe and isolated
    engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        # SQLite-specific optimizations
        connect_args={
            "check_same_thread": False,  # Allow sharing connection across threads
            "timeout": 20,  # Connection timeout
        },
        # Disable pooling for SQLite in-memory (each connection gets its own DB)
        poolclass=None,
    )
    
    return engine


def create_test_tables(engine):
    """Create all tables in test database."""
    # Import to ensure all models are loaded
    Base.metadata.create_all(bind=engine, checkfirst=True)


def drop_test_tables(engine):
    """Drop all tables in test database."""
    # Import to ensure all models are loaded
    Base.metadata.drop_all(bind=engine)


# Test session factory
TestSessionLocal = None


def init_test_db():
    """Initialize test database session factory."""
    global TestSessionLocal
    engine = create_test_engine()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestSessionLocal