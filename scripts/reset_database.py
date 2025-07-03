#!/usr/bin/env python3
"""
Reset database - remove all user data (keeps schema intact).
Use with caution!
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infra.database.models.user import (
    User, UserProfile, UserPreference, UserDietaryPreference,
    UserHealthCondition, UserAllergy, UserGoal
)
from src.infra.database.models.tdee_calculation import TdeeCalculation
from src.infra.database.models.meal_plan import MealPlan, Conversation

def reset_user_data():
    """Remove all user-related data from database."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mealtrack.db')
    engine = create_engine(f'sqlite:///{db_path}')
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    print("⚠️  Database Reset Tool")
    print("=" * 60)
    print("This will DELETE all user data including:")
    print("- Users and profiles")
    print("- Preferences and goals")
    print("- TDEE calculations")
    print("- Meal plans and conversations")
    print("\nThe database schema will remain intact.")
    
    response = input("\nAre you SURE you want to delete all user data? (type 'DELETE' to confirm): ")
    
    if response != "DELETE":
        print("Cancelled.")
        return
    
    try:
        # Delete in order to respect foreign keys
        print("\n🗑️  Deleting data...")
        
        # Delete TDEE calculations
        count = session.query(TdeeCalculation).count()
        session.query(TdeeCalculation).delete()
        print(f"   Deleted {count} TDEE calculations")
        
        # Delete meal plans and conversations
        count = session.query(MealPlan).count()
        session.query(MealPlan).delete()
        print(f"   Deleted {count} meal plans")
        
        count = session.query(Conversation).count()
        session.query(Conversation).delete()
        print(f"   Deleted {count} conversations")
        
        # Delete user preferences (cascades to dietary, health, allergies)
        count = session.query(UserPreference).count()
        session.query(UserPreference).delete()
        print(f"   Deleted {count} user preferences")
        
        # Delete user goals
        count = session.query(UserGoal).count()
        session.query(UserGoal).delete()
        print(f"   Deleted {count} user goals")
        
        # Delete user profiles
        count = session.query(UserProfile).count()
        session.query(UserProfile).delete()
        print(f"   Deleted {count} user profiles")
        
        # Delete users
        count = session.query(User).count()
        session.query(User).delete()
        print(f"   Deleted {count} users")
        
        session.commit()
        print("\n✅ All user data has been deleted.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    reset_user_data()