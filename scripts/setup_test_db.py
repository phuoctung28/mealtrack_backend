#!/usr/bin/env python3
"""
Setup test database for local testing.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.infra.database.test_config import get_test_database_url, create_test_tables


def setup_test_database():
    """Create test database and tables."""
    print("Setting up test database...")
    
    # Get database URL and extract database name
    db_url = get_test_database_url()
    db_name = db_url.rsplit('/', 1)[1].split('?')[0]
    server_url = db_url.rsplit('/', 1)[0]
    
    print(f"Database URL: {server_url}/***")
    print(f"Database name: {db_name}")
    
    # Create database if it doesn't exist
    print(f"Creating database '{db_name}' if it doesn't exist...")
    temp_engine = create_engine(server_url, isolation_level='AUTOCOMMIT')
    
    with temp_engine.connect() as conn:
        # Check if database exists
        result = conn.execute(
            text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
        )
        if result.fetchone():
            print(f"Database '{db_name}' already exists.")
            response = input("Do you want to drop and recreate it? (y/N): ")
            if response.lower() == 'y':
                conn.execute(text(f"DROP DATABASE {db_name}"))
                print(f"Dropped database '{db_name}'.")
                conn.execute(text(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                print(f"Created database '{db_name}'.")
            else:
                print("Keeping existing database.")
        else:
            conn.execute(text(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            print(f"Created database '{db_name}'.")
    
    temp_engine.dispose()
    
    # Create tables
    print("Creating tables...")
    engine = create_engine(db_url)
    create_test_tables(engine)
    engine.dispose()
    
    print("Test database setup complete!")
    print(f"\nTo run tests locally, make sure these environment variables are set:")
    print(f"  TEST_DB_HOST={os.getenv('TEST_DB_HOST', 'localhost')}")
    print(f"  TEST_DB_PORT={os.getenv('TEST_DB_PORT', '3306')}")
    print(f"  TEST_DB_USER={os.getenv('TEST_DB_USER', 'root')}")
    print(f"  TEST_DB_PASSWORD=***")
    print(f"  TEST_DB_NAME={os.getenv('TEST_DB_NAME', 'mealtrack_test')}")


if __name__ == "__main__":
    setup_test_database()