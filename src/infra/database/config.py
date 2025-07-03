import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Check for Railway's DATABASE_URL first, then fall back to individual variables
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway or other platform provides DATABASE_URL
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    # Replace mysql:// with mysql+pymysql:// if needed
    if SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
    USE_SQLITE = False
else:
    # Use individual environment variables (existing setup)
    # Get database connection details from environment variables
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "mealtrack")

    # Use SQLite for development
    USE_SQLITE = os.getenv("USE_SQLITE", "1") == "1"

    if USE_SQLITE:
        # SQLite URL
        SQLALCHEMY_DATABASE_URL = "sqlite:///./mealtrack.db"
    else:
        # MySQL URL
        SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine based on database type
if DATABASE_URL or (not USE_SQLITE):
    # MySQL/PostgreSQL configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,  # Set to True to log SQL queries
        pool_pre_ping=True,  # Check connections before using them
        pool_recycle=300,  # Recycle connections every 5 minutes
    )
else:
    # SQLite configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        echo=False,  # Set to True to log SQL queries
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

def get_db():
    """
    Dependency for FastAPI to get a database session.
    
    Usage:
    ```
    @app.get("/items/")
    def get_items(db: Session = Depends(get_db)):
        # Use db session
        pass
    ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 