"""
Test database configuration using MySQL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .config import Base


def get_test_database_url() -> str:
    """Get database URL for testing."""
    # Check if we're in CI environment
    if os.getenv("CI"):
        return "mysql+pymysql://test_user:test_password@localhost:3306/mealtrack_test"
    
    # Local testing database
    return (
        f"mysql+pymysql://{os.getenv('TEST_DB_USER', 'root')}:"
        f"{os.getenv('TEST_DB_PASSWORD', '')}@"
        f"{os.getenv('TEST_DB_HOST', 'localhost')}:"
        f"{os.getenv('TEST_DB_PORT', '3306')}/"
        f"{os.getenv('TEST_DB_NAME', 'mealtrack_test')}"
    )


def create_test_engine():
    """Create test database engine with appropriate settings."""
    database_url = get_test_database_url()
    
    # Use smaller pool size for tests
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        pool_recycle=3600,
        echo=False  # Set to True for SQL debugging
    )
    
    return engine


def create_test_tables(engine):
    """Create all tables in test database."""
    Base.metadata.create_all(bind=engine)


def drop_test_tables(engine):
    """Drop all tables in test database."""
    Base.metadata.drop_all(bind=engine)


# Test session factory
TestSessionLocal = None


def init_test_db():
    """Initialize test database session factory."""
    global TestSessionLocal
    engine = create_test_engine()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestSessionLocal