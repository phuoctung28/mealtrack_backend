import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# SSL configuration from environment variables
SSL_ENABLED = os.getenv("DB_SSL_ENABLED", "true").lower() == "true"
SSL_VERIFY_CERT = os.getenv("DB_SSL_VERIFY_CERT", "false").lower() == "true"
SSL_VERIFY_IDENTITY = os.getenv("DB_SSL_VERIFY_IDENTITY", "false").lower() == "true"

# Check for DATABASE_URL first, then fall back to individual variables
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Platform provides DATABASE_URL
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    # Replace mysql:// with mysql+pymysql:// if needed
    if SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
else:
    # Use individual environment variables
    # Get database connection details from environment variables
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "mealtrack")

    # MySQL URL
    SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine for MySQL/PostgreSQL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,  # Set to True to log SQL queries
    pool_pre_ping=True,  # Check connections before using them
    pool_recycle=300,  # Recycle connections every 5 minutes
    # Database connection pool settings
    pool_size=5,  # Connection pool size
    max_overflow=10,  # Allow some overflow connections
    pool_timeout=30,  # Wait up to 30 seconds for available connection
    # Connection retry and timeout settings
    connect_args={
        "connect_timeout": 60,  # 60 second connection timeout
        "read_timeout": 60,     # 60 second read timeout
        "write_timeout": 60,    # 60 second write timeout
        "charset": "utf8mb4",
        "autocommit": False,
        # SSL configuration for secure connections (required by Northflank)
        "ssl_disabled": not SSL_ENABLED,  # Enable SSL based on environment
        "ssl_verify_cert": SSL_VERIFY_CERT,  # Certificate verification from environment
        "ssl_verify_identity": SSL_VERIFY_IDENTITY,  # Identity verification from environment
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

def get_db():
    """
    Dependency for FastAPI to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 