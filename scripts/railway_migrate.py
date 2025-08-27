#!/usr/bin/env python
"""
Railway-specific migration script.
This script handles database migrations for Railway deployment with proper error handling.
"""
import os
import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def wait_for_database(max_attempts=10, delay=5):
    """Wait for database to be available with exponential backoff."""
    logger.info("⏳ Waiting for database to be available...")
    
    for attempt in range(max_attempts):
        try:
            from src.infra.database.config import engine
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
            
        except Exception as e:
            if attempt < max_attempts - 1:
                wait_time = delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Database connection failed after {max_attempts} attempts")
                raise
    
    return False


def run_migrations():
    """Run database migrations with proper error handling."""
    try:
        # Wait for database to be available
        wait_for_database()
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Check current migration status
        logger.info("📋 Checking current migration status...")
        
        # Get current revision
        try:
            from alembic.script import ScriptDirectory
            script_dir = ScriptDirectory.from_config(alembic_cfg)
            heads = script_dir.get_heads()
            logger.info(f"Available migration heads: {heads}")
        except Exception as e:
            logger.warning(f"Could not determine migration heads: {e}")
        
        # Check if alembic_version table exists
        from src.infra.database.config import engine
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'alembic_version' not in tables:
            logger.info("🆕 First deployment - initializing migrations...")
            
            # Check if database is empty
            app_tables = [t for t in tables if t != 'alembic_version']
            
            if not app_tables:
                logger.info("📝 Empty database detected - stamping baseline migration")
                command.stamp(alembic_cfg, "001")
                logger.info("✅ Baseline migration stamped")
            else:
                logger.warning("⚠️  Database has tables but no alembic_version - this might cause issues")
        
        # Run migrations
        logger.info("🚀 Running migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ All migrations completed successfully")
        
        # Verify final state
        inspector = inspect(engine)
        final_tables = inspector.get_table_names()
        app_tables = [t for t in final_tables if t != 'alembic_version']
        logger.info(f"📊 Database now has {len(app_tables)} application tables")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        logger.error("Migration error details:", exc_info=True)
        return False


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("🚂 Railway Migration Script Starting")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'production')}")
    logger.info(f"Database URL: {os.environ.get('DATABASE_URL', 'Not set')[:50]}...")
    logger.info("=" * 60)
    
    try:
        success = run_migrations()
        if success:
            logger.info("🎉 Migration process completed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 Migration process failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
