"""
Test database configuration using MySQL for consistency with production.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from src.infra.database.config import Base

# Load environment variables
load_dotenv()


def get_test_database_url() -> str:
    """Get database URL for testing."""
    # Check if DATABASE_URL is set (for CI compatibility)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Replace mysql:// with mysql+pymysql:// if needed for SQLAlchemy compatibility
        if database_url.startswith("mysql://"):
            database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
        return database_url
    
    # Use individual environment variables for local testing
    # Uses same MySQL container but different database name
    test_db_user = os.getenv("TEST_DB_USER", "root")
    test_db_password = os.getenv("TEST_DB_PASSWORD", "rootpassword123")
    test_db_host = os.getenv("TEST_DB_HOST", "localhost")
    test_db_port = os.getenv("TEST_DB_PORT", "3306")  # Use same MySQL container
    test_db_name = os.getenv("TEST_DB_NAME", "mealtrack_test")
    
    return f"mysql+pymysql://{test_db_user}:{test_db_password}@{test_db_host}:{test_db_port}/{test_db_name}"


def create_test_engine():
    """Create test database engine with MySQL configuration."""
    database_url = get_test_database_url()
    
    # MySQL configuration optimized for testing
    engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Check connections before using them
        pool_recycle=300,  # Recycle connections every 5 minutes
        # Test-optimized settings
        pool_size=5,  # Smaller pool size for tests
        max_overflow=5,  # Limited overflow for tests
        pool_timeout=30,  # Wait up to 30 seconds for available connection
        # Connection settings
        connect_args={
            "connect_timeout": 60,  # 60 second connection timeout
            "read_timeout": 60,     # 60 second read timeout
            "write_timeout": 60,    # 60 second write timeout
            "charset": "utf8mb4",
            "autocommit": False,
        }
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