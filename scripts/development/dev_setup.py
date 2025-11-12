#!/usr/bin/env python
"""
Development database setup script.
This script is for LOCAL DEVELOPMENT ONLY and should never be used in production.
"""
import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infra.database.config import engine, Base
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_dev_database():
    """Set up database for local development."""
    try:
        # Check if we should recreate tables
        RECREATE_TABLES = os.getenv("RECREATE_TABLES", "false").lower() == "true"
        
        # Check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Count non-system tables
        app_tables = [t for t in existing_tables if t != 'alembic_version']
        
        if RECREATE_TABLES and app_tables:
            logger.warning("RECREATE_TABLES=true. Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            logger.info("All tables dropped.")
            app_tables = []
        
        if len(app_tables) == 0:
            logger.info("Creating database schema for development...")
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Development database schema created successfully!")
        else:
            logger.info(f"✅ Development database ready with {len(app_tables)} existing tables")
            
    except Exception as e:
        logger.error(f"Development database setup failed: {e}")
        logger.error("Ensure MySQL is running: ./scripts/local.sh")
        raise


if __name__ == "__main__":
    logger.info("🔧 Setting up development database...")
    setup_dev_database()
    logger.info("✅ Development database setup complete!")
