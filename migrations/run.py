#!/usr/bin/env python
"""
Database migration runner with retry logic and proper error handling.

This script runs Alembic migrations with:
- Database connection retry with exponential backoff
- Proper first-time initialization
- Detailed logging
- Clean error handling
"""
import os
import sys
import logging
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, DatabaseError
from src.infra.database.config import engine, Base

# Configure logging with timestamp
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2.0  # seconds
MAX_RETRY_DELAY = 30.0  # seconds
ALEMBIC_CONFIG_PATH = "alembic.ini"


def wait_for_database(max_retries: int = MAX_RETRIES) -> bool:
    """
    Wait for database to become available with exponential backoff.
    
    Args:
        max_retries: Maximum number of connection attempts
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    delay = INITIAL_RETRY_DELAY
    
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()  # Ensure query completes
                conn.commit()  # Explicitly commit
            logger.info("✅ Database connection established")
            return True
            
        except (OperationalError, DatabaseError) as e:
            if attempt == max_retries:
                logger.error(f"❌ Failed to connect after {max_retries} attempts: {e}")
                return False
            
            logger.warning(f"Database not ready (attempt {attempt}/{max_retries}), retrying in {delay}s...")
            time.sleep(delay)
            delay = min(delay * 2, MAX_RETRY_DELAY)  # Exponential backoff with cap
    
    return False


def get_alembic_config() -> Optional[Config]:
    """
    Load and validate Alembic configuration.
    
    Returns:
        Config object if successful, None otherwise
    """
    config_path = Path(ALEMBIC_CONFIG_PATH)
    
    if not config_path.exists():
        logger.error(f"❌ Alembic config not found: {config_path.absolute()}")
        return None
    
    try:
        alembic_cfg = Config(str(config_path))
        # Ensure database URL is set from engine
        alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
        return alembic_cfg
        
    except Exception as e:
        logger.error(f"❌ Failed to load Alembic config: {e}")
        return None


def initialize_first_deployment(alembic_cfg: Config) -> bool:
    """
    Initialize database for first deployment.
    
    Args:
        alembic_cfg: Alembic configuration object
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"📊 Found {len(tables)} existing tables")
        
        # Check if we have any application tables (excluding alembic_version)
        app_tables = [t for t in tables if t != 'alembic_version']
        
        if not app_tables:
            logger.info("Empty database detected, creating initial schema...")
            # Import all models to ensure they're registered
            from src.infra.database import models  # noqa: F401
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Initial schema created")
        else:
            logger.info(f"Database has existing tables: {', '.join(app_tables[:5])}...")
        
        # Stamp database with latest revision (not hardcoded)
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        head_revision = script_dir.get_current_head()
        
        if head_revision:
            logger.info(f"Stamping database with revision: {head_revision}")
            command.stamp(alembic_cfg, head_revision)
            logger.info("✅ Database stamped successfully")
        else:
            logger.warning("No head revision found, stamping with 'head'")
            command.stamp(alembic_cfg, "head")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ First deployment initialization failed: {e}", exc_info=True)
        return False


def run_migrations() -> bool:
    """
    Run database migrations with proper error handling.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("🚀 Starting database migration process...")
    
    # Step 1: Wait for database
    if not wait_for_database():
        logger.error("❌ Cannot proceed without database connection")
        return False
    
    # Step 2: Load Alembic config
    alembic_cfg = get_alembic_config()
    if not alembic_cfg:
        return False
    
    try:
        # Step 3: Check current state
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Step 4: Handle first deployment
        if 'alembic_version' not in tables:
            logger.info("🆕 First deployment detected, initializing...")
            if not initialize_first_deployment(alembic_cfg):
                return False
        else:
            logger.info("📋 Existing deployment detected")
        
        # Step 5: Run migrations
        logger.info("⏩ Running pending migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ All migrations completed successfully")
        
        # Step 6: Verify final state
        from alembic.runtime.migration import MigrationContext
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            logger.info(f"📌 Current database revision: {current_rev}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    try:
        success = run_migrations()
        exit_code = 0 if success else 1
        
        if success:
            logger.info("🎉 Migration process completed successfully")
        else:
            logger.error("💥 Migration process failed")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.warning("⚠️ Migration interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}", exc_info=True)
        sys.exit(1)