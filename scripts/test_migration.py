#!/usr/bin/env python
"""
Test script to verify migrations work correctly.
This script will test the migration system with our new test table.
"""
import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from src.infra.database.config import engine
from sqlalchemy import inspect, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_migration():
    """Test the migration system."""
    try:
        # Check if we can connect
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Check current migration status
        logger.info("📋 Current migration status:")
        from alembic.script import ScriptDirectory
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        heads = script_dir.get_heads()
        logger.info(f"Current heads: {heads}")
        
        # Check if test_table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'test_table' in tables:
            logger.info("✅ test_table already exists")
            
            # Show table structure
            columns = inspector.get_columns('test_table')
            logger.info("📊 test_table structure:")
            for col in columns:
                logger.info(f"  - {col['name']}: {col['type']} (nullable: {col['nullable']})")
        else:
            logger.info("⚠️  test_table does not exist yet")
            logger.info("💡 Run 'alembic upgrade head' to apply migrations")
        
        # Test inserting data into test_table if it exists
        if 'test_table' in tables:
            with engine.connect() as conn:
                # Insert test data
                result = conn.execute(text("""
                    INSERT INTO test_table (name, description, test_number, created_at, updated_at)
                    VALUES (:name, :description, :test_number, NOW(), NOW())
                """), {
                    "name": "Test Entry",
                    "description": "This is a test entry",
                    "test_number": 42
                })
                conn.commit()
                logger.info("✅ Successfully inserted test data into test_table")
                
                # Query the data back
                result = conn.execute(text("SELECT * FROM test_table"))
                rows = result.fetchall()
                logger.info(f"📊 Found {len(rows)} rows in test_table")
                for row in rows:
                    logger.info(f"  - ID: {row[0]}, Name: {row[1]}, Number: {row[3]}")
        
    except Exception as e:
        logger.error(f"❌ Migration test failed: {e}")
        raise


if __name__ == "__main__":
    logger.info("🧪 Testing migration system...")
    test_migration()
    logger.info("✅ Migration test completed!")
