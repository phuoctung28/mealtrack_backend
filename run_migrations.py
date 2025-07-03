#!/usr/bin/env python3
"""
Fix and run the user migration for SQLite database.

This script will:
1. Check current migration status
2. Apply any pending migrations
3. Show the final database schema
"""

import os
import sys
import sqlite3

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_current_status():
    """Check current database and migration status."""
    print("🔍 Checking current database status...")
    
    try:
        conn = sqlite3.connect('mealtrack.db')
        cursor = conn.cursor()
        
        # Get current migration version
        cursor.execute("SELECT version_num FROM alembic_version;")
        version = cursor.fetchone()
        current_version = version[0] if version else "None"
        print(f"📌 Current migration version: {current_version}")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [t[0] for t in cursor.fetchall() if not t[0].startswith('sqlite_')]
        print(f"📊 Current tables: {', '.join(tables)}")
        
        conn.close()
        return current_version
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return None

def run_migration():
    """Run the migration using Alembic."""
    print("\n🚀 Running migrations...")
    
    try:
        from alembic import command
        from alembic.config import Config
        
        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")
        
        # Get current version
        current = check_current_status()
        
        if current == "004":
            print("Running migration 005 (meal planning tables)...")
            command.upgrade(alembic_cfg, "005")
            print("✅ Migration 005 completed")
            
        current = check_current_status()
        if current == "005":
            print("\nRunning migration 006 (user and TDEE tables)...")
            command.upgrade(alembic_cfg, "006")
            print("✅ Migration 006 completed")
            
        print("\n✨ All migrations completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False
    
    return True

def verify_schema():
    """Verify the final database schema."""
    print("\n📋 Verifying database schema...")
    
    try:
        conn = sqlite3.connect('mealtrack.db')
        cursor = conn.cursor()
        
        # Expected tables
        expected_tables = {
            'users': ['id', 'email', 'username', 'password_hash', 'is_active'],
            'user_profiles': ['id', 'user_id', 'age', 'gender', 'height_cm', 'weight_kg'],
            'user_preferences': ['id', 'user_id'],
            'user_dietary_preferences': ['id', 'user_preference_id', 'preference'],
            'user_health_conditions': ['id', 'user_preference_id', 'condition'],
            'user_allergies': ['id', 'user_preference_id', 'allergen'],
            'user_goals': ['id', 'user_id', 'activity_level', 'fitness_goal'],
            'tdee_calculations': ['id', 'user_id', 'bmr', 'tdee', 'target_calories']
        }
        
        print("\n🔍 Checking new user tables:")
        print("-" * 50)
        
        for table_name, expected_cols in expected_tables.items():
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            exists = cursor.fetchone() is not None
            
            if exists:
                # Get column info
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"✅ {table_name}: {len(columns)} columns")
            else:
                print(f"❌ {table_name}: NOT FOUND")
        
        # Check if meal_plans and conversations have new_user_id column
        print("\n🔗 Checking foreign key columns:")
        for table in ['meal_plans', 'conversations']:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [col[1] for col in cursor.fetchall()]
            has_new_user_id = 'new_user_id' in columns
            status = "✅" if has_new_user_id else "❌"
            print(f"{status} {table}.new_user_id")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")

def main():
    """Main function."""
    print("🗄️  MealTrack Database Migration Tool")
    print("=" * 50)
    
    # Check current status
    current = check_current_status()
    
    if current == "006":
        print("\n✅ Database is already up to date!")
        verify_schema()
    else:
        # Run migrations
        if run_migration():
            verify_schema()
        else:
            print("\n❌ Migration failed. Please check the errors above.")
            sys.exit(1)
    
    print("\n✅ Done! Your database now has user and TDEE tables.")
    print("\nNext steps:")
    print("1. Test the new endpoints at /v1/user-onboarding/save")
    print("2. Implement user authentication")
    print("3. Update existing endpoints to use real user IDs")

if __name__ == "__main__":
    main()