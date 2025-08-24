#!/usr/bin/env python3
"""
Clean up database by dropping all tables and recreating them.

Usage:
    python scripts/cleanup_db.py
    
This will:
1. Drop all existing tables
2. Recreate the database schema
3. Optionally populate with mock data
"""

import argparse
import os
import sys

from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infra.database.config import engine, Base, SQLALCHEMY_DATABASE_URL


def drop_all_tables():
    """Drop all tables in the database."""
    print("🗑️  Dropping all tables...")
    
    with engine.connect() as conn:
        # Get inspector
        inspector = inspect(engine)
        
        # Get all table names
        tables = inspector.get_table_names()
        
        if not tables:
            print("ℹ️  No tables found in database")
            return
        
        # Disable foreign key checks for MySQL
        if 'mysql' in SQLALCHEMY_DATABASE_URL:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.commit()
        
        # Drop each table
        for table in tables:
            try:
                print(f"   Dropping table: {table}")
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                conn.commit()
            except Exception as e:
                print(f"   ⚠️  Error dropping {table}: {e}")
        
        # Re-enable foreign key checks for MySQL
        if 'mysql' in SQLALCHEMY_DATABASE_URL:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
    
    print("✅ All tables dropped")


def truncate_all_tables():
    """Truncate all tables (remove data but keep structure)."""
    print("🗑️  Truncating all tables (removing data)...")
    
    with engine.connect() as conn:
        # Get inspector
        inspector = inspect(engine)
        
        # Get all table names
        tables = inspector.get_table_names()
        
        if not tables:
            print("ℹ️  No tables found in database")
            return
        
        # Disable foreign key checks for MySQL
        if 'mysql' in SQLALCHEMY_DATABASE_URL:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.commit()
        
        # Truncate each table
        truncated_count = 0
        for table in tables:
            try:
                print(f"   Truncating table: {table}")
                conn.execute(text(f"TRUNCATE TABLE {table}"))
                conn.commit()
                truncated_count += 1
            except Exception as e:
                # Some tables might not support TRUNCATE, try DELETE
                try:
                    conn.execute(text(f"DELETE FROM {table}"))
                    conn.commit()
                    truncated_count += 1
                except Exception as e2:
                    print(f"   ⚠️  Could not truncate {table}: {e2}")
        
        # Re-enable foreign key checks for MySQL
        if 'mysql' in SQLALCHEMY_DATABASE_URL:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
    
    print(f"✅ Truncated {truncated_count} tables - all data removed")


def create_all_tables():
    """Create all tables from SQLAlchemy models."""
    print("\n🔨 Creating database schema...")
    
    # Import all models to ensure they're registered

    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Verify tables were created
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"✅ Created {len(tables)} tables:")
    for table in sorted(tables):
        print(f"   - {table}")


def populate_mock_data():
    """Populate database with mock data."""
    print("\n📊 Populating mock data...")
    
    try:
        from scripts.populate_mock_data import main as populate_main
        populate_main()
        print("✅ Mock data populated")
    except Exception as e:
        print(f"⚠️  Error populating mock data: {e}")
        print("   You can run 'python scripts/populate_mock_data.py' manually later")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Clean up database")
    parser.add_argument(
        "--truncate-only",
        action="store_true",
        help="Only truncate tables (remove data), don't drop and recreate"
    )
    parser.add_argument(
        "--no-mock-data",
        action="store_true",
        help="Skip populating mock data (only applies when recreating tables)"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    print("🧹 MealTrack Database Cleanup")
    print("=" * 60)
    print(f"Database: {SQLALCHEMY_DATABASE_URL.split('@')[1] if '@' in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL}")
    print()
    
    if args.truncate_only:
        action_desc = "TRUNCATE ALL TABLES (remove all data)"
    else:
        action_desc = "DROP AND RECREATE ALL TABLES"
    
    if not args.yes:
        response = input(f"⚠️  This will {action_desc}. Continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Cancelled")
            return
    
    try:
        if args.truncate_only:
            # Just truncate tables
            truncate_all_tables()
        else:
            # Drop and recreate tables
            drop_all_tables()
            create_all_tables()
            
            # Optionally populate mock data
            if not args.no_mock_data:
                populate_mock_data()
        
        print("\n✨ Database cleanup complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()