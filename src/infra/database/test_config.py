"""
Test database configuration using MySQL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infra.database.config import Base


def get_test_database_url() -> str:
    """Get database URL for testing."""
    # Check for DATABASE_URL first (same pattern as production)
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # Replace mysql:// with mysql+pymysql:// if needed
        if database_url.startswith("mysql://"):
            database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
        return database_url
    
    # Fall back to individual variables for local testing
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
    from sqlalchemy import MetaData
    
    # Import to ensure all models are loaded
    import src.infra.database.models
    
    # Use reflection to find and drop ALL tables in the database
    meta = MetaData()
    meta.reflect(bind=engine)
    meta.drop_all(bind=engine)
    
    # Also try to drop using Base metadata in case reflection missed any
    Base.metadata.drop_all(bind=engine)


# Test session factory
TestSessionLocal = None


def init_test_db():
    """Initialize test database session factory."""
    global TestSessionLocal
    engine = create_test_engine()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestSessionLocal