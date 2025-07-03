#!/usr/bin/env python3
"""
Fix migration version to match actual database state.

This script will update the alembic version to 006 since all the tables
already exist in the database.
"""

import sqlite3
import sys

def check_tables_exist():
    """Check if all user tables exist."""
    required_tables = [
        'users', 'user_profiles', 'user_preferences', 
        'user_dietary_preferences', 'user_health_conditions', 
        'user_allergies', 'user_goals', 'tdee_calculations'
    ]
    
    try:
        conn = sqlite3.connect('mealtrack.db')
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print("📊 Checking required user tables:")
        print("-" * 50)
        
        all_exist = True
        for table in required_tables:
            exists = table in existing_tables
            status = "✅" if exists else "❌"
            print(f"{status} {table}")
            if not exists:
                all_exist = False
        
        # Check for new_user_id columns
        print("\n🔗 Checking foreign key columns:")
        for table in ['meal_plans', 'conversations']:
            if table in existing_tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = [col[1] for col in cursor.fetchall()]
                has_new_user_id = 'new_user_id' in columns
                status = "✅" if has_new_user_id else "⚠️"
                print(f"{status} {table}.new_user_id {'exists' if has_new_user_id else 'missing'}")
        
        conn.close()
        return all_exist
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def update_migration_version():
    """Update alembic version to 006."""
    try:
        conn = sqlite3.connect('mealtrack.db')
        cursor = conn.cursor()
        
        # Get current version
        cursor.execute("SELECT version_num FROM alembic_version;")
        current = cursor.fetchone()
        print(f"\n📌 Current migration version: {current[0] if current else 'None'}")
        
        # Update to version 006
        cursor.execute("DELETE FROM alembic_version;")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('006');")
        conn.commit()
        
        # Verify update
        cursor.execute("SELECT version_num FROM alembic_version;")
        new_version = cursor.fetchone()
        print(f"✅ Updated migration version to: {new_version[0]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating version: {e}")
        return False

def add_missing_columns():
    """Add new_user_id columns if they don't exist."""
    try:
        conn = sqlite3.connect('mealtrack.db')
        cursor = conn.cursor()
        
        # Check and add new_user_id to meal_plans
        cursor.execute("PRAGMA table_info(meal_plans);")
        meal_plans_cols = [col[1] for col in cursor.fetchall()]
        
        if 'new_user_id' not in meal_plans_cols:
            print("\n➕ Adding new_user_id to meal_plans table...")
            cursor.execute("ALTER TABLE meal_plans ADD COLUMN new_user_id VARCHAR(36);")
            print("✅ Added new_user_id to meal_plans")
        
        # Check and add new_user_id to conversations
        cursor.execute("PRAGMA table_info(conversations);")
        conversations_cols = [col[1] for col in cursor.fetchall()]
        
        if 'new_user_id' not in conversations_cols:
            print("➕ Adding new_user_id to conversations table...")
            cursor.execute("ALTER TABLE conversations ADD COLUMN new_user_id VARCHAR(36);")
            print("✅ Added new_user_id to conversations")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        return False

def main():
    """Main function."""
    print("🔧 MealTrack Migration Version Fix")
    print("=" * 50)
    
    # Check if all tables exist
    if check_tables_exist():
        print("\n✅ All user tables exist in the database.")
        
        # Add missing columns if needed
        add_missing_columns()
        
        # Update migration version
        if update_migration_version():
            print("\n✨ Migration version fixed successfully!")
            print("\nYour database is now properly configured with:")
            print("- All user and TDEE tables")
            print("- Migration version set to 006")
            print("- Foreign key columns added to existing tables")
            print("\nYou can now use the user onboarding endpoints!")
        else:
            print("\n❌ Failed to update migration version.")
            sys.exit(1)
    else:
        print("\n❌ Not all required tables exist. Please run create_fresh_db.py instead.")
        sys.exit(1)

if __name__ == "__main__":
    main()