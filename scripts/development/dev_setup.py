#!/usr/bin/env python
"""
Development database setup script.
This script is for LOCAL DEVELOPMENT ONLY and should never be used in production.

⚠️ DEPRECATED: Use migrations/run.py instead

This script creates tables directly from SQLAlchemy models using Base.metadata.create_all(),
which bypasses Alembic migrations. This means:
- ❌ Migration-specific logic (CHECK constraints, data transforms) won't be applied
- ❌ Database state may differ from production
- ❌ alembic_version table won't be properly stamped

RECOMMENDED: Use migrations/run.py which properly handles migrations with retry logic.

This script is kept for:
- Emergency database recreation during development
- Testing specific scenarios that need a clean slate
- Understanding the base schema without migrations
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infra.database.config import engine, Base
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Warn if not running in virtual environment
venv_path = project_root / ".venv"
is_in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
if venv_path.exists() and not is_in_venv:
    venv_python = venv_path / "bin" / "python"
    if venv_python.exists():
        logger.warning(
            "⚠️  Warning: Script is not running in virtual environment.\n"
            f"Please activate venv first: source .venv/bin/activate\n"
            f"Or run with venv Python: {venv_python} {sys.argv[0]}"
        )


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
