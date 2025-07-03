#!/usr/bin/env python3
"""
Create a fresh database with all tables.
Use this if migrations are causing issues.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_fresh_database():
    """Create a fresh database with all tables."""
    from sqlalchemy import create_engine
    from src.infra.database.config import Base
    
    # Import all models to register them with Base
    from src.infra.database.models import (
        Meal, MealImage, Nutrition, FoodItem,
        MealPlan, MealPlanDay, PlannedMeal, Conversation, ConversationMessage,
        User, UserProfile, UserPreference, UserDietaryPreference,
        UserHealthCondition, UserAllergy, UserGoal, TdeeCalculation
    )
    
    # Backup existing database if it exists
    if os.path.exists('mealtrack.db'):
        import shutil
        backup_name = 'mealtrack_backup.db'
        print(f"📦 Backing up existing database to {backup_name}")
        shutil.copy('mealtrack.db', backup_name)
    
    # Create new database
    print("🗄️  Creating fresh database with all tables...")
    engine = create_engine('sqlite:///mealtrack.db')
    
    # Drop all existing tables
    Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Add alembic version table and set to latest version
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """))
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('006')"))
        conn.commit()
    
    print("✅ Fresh database created successfully!")
    
    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n📊 Created {len(tables)} tables:")
    for table in sorted(tables):
        if not table.startswith('sqlite_'):
            print(f"  • {table}")
    
    print("\n✨ Database is ready to use!")

if __name__ == "__main__":
    response = input("⚠️  This will create a fresh database. Continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        create_fresh_database()
    else:
        print("Cancelled.")