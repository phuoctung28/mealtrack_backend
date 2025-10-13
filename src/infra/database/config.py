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

# Debug logging for SSL configuration
import logging
logger = logging.getLogger(__name__)
logger.info(f"SSL Configuration: enabled={SSL_ENABLED}, verify_cert={SSL_VERIFY_CERT}, verify_identity={SSL_VERIFY_IDENTITY}")

# Check for DATABASE_URL first, then fall back to individual variables
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Platform provides DATABASE_URL
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    # Replace mysql:// with mysql+mysqlconnector:// if needed (better SSL support)
    if SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql://", "mysql+mysqlconnector://", 1)
    elif SQLALCHEMY_DATABASE_URL.startswith("mysql+pymysql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql+pymysql://", "mysql+mysqlconnector://", 1)
    
    # Add SSL parameters to URL if SSL is enabled
    if SSL_ENABLED:
        ssl_params = []
        # Use explicit SSL parameters for mysql-connector-python
        ssl_params.append("ssl_disabled=false")
        ssl_params.append(f"ssl_verify_cert={str(SSL_VERIFY_CERT).lower()}")
        ssl_params.append(f"ssl_verify_identity={str(SSL_VERIFY_IDENTITY).lower()}")
        ssl_params.append("ssl_ca=")  # Empty CA for cloud providers
        
        # Check if URL already has parameters
        if "?" in SQLALCHEMY_DATABASE_URL:
            # URL already has parameters, append SSL params
            SQLALCHEMY_DATABASE_URL += "&" + "&".join(ssl_params)
        else:
            # URL has no parameters, add SSL params
            SQLALCHEMY_DATABASE_URL += "?" + "&".join(ssl_params)
        
        # Log the final URL (mask password for security)
        masked_url = SQLALCHEMY_DATABASE_URL
        if '://' in masked_url and '@' in masked_url:
            parts = masked_url.split('://')
            if ':' in parts[1] and '@' in parts[1]:
                auth_host = parts[1].split('@')[0]
                if ':' in auth_host:
                    user = auth_host.split(':')[0]
                    masked_url = masked_url.replace(auth_host, f'{user}:***')
        logger.info(f"Final Database URL: {masked_url}")
        logger.info(f"SSL Parameters added: {ssl_params}")
else:
    # Use individual environment variables
    # Get database connection details from environment variables
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "mealtrack")

    # MySQL URL with SSL parameters (using mysqlconnector for better SSL support)
    base_url = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    if SSL_ENABLED:
        ssl_params = []
        ssl_params.append("ssl_disabled=false")
        ssl_params.append(f"ssl_verify_cert={str(SSL_VERIFY_CERT).lower()}")
        ssl_params.append(f"ssl_verify_identity={str(SSL_VERIFY_IDENTITY).lower()}")
        ssl_params.append("ssl_ca=")  # Empty CA for cloud providers
        SQLALCHEMY_DATABASE_URL = base_url + "?" + "&".join(ssl_params)
    else:
        SQLALCHEMY_DATABASE_URL = base_url

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
        "connection_timeout": 60,  # 60 second connection timeout (mysql-connector-python uses connection_timeout not connect_timeout)
        "charset": "utf8mb4",
        "autocommit": False,
        # SSL fallback configuration (mysql-connector-python specific)
        "ssl_disabled": False,
        "ssl_verify_cert": SSL_VERIFY_CERT,
        "ssl_verify_identity": SSL_VERIFY_IDENTITY,
        "ssl_ca": "",  # Empty CA for cloud providers
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