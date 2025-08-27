#!/usr/bin/env python
"""
Simple migration runner for Railway.
"""
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from src.infra.database.config import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run database migrations."""
    try:
        # Check connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("✅ Database connected")
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Check if first time
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'alembic_version' not in tables:
            logger.info("First deployment - initializing migrations...")
            
            # Create tables if empty database
            if not [t for t in tables if t != 'alembic_version']:
                Base.metadata.create_all(bind=engine)
                logger.info("Created initial schema")
            
            # Mark as baseline
            command.stamp(alembic_cfg, "001")
            logger.info("Stamped baseline migration")
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations complete")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)