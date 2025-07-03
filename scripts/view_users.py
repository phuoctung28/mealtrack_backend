#!/usr/bin/env python3
"""
View all users and their profile IDs in the database.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infra.database.models.user import User, UserProfile, UserGoal, UserPreference
from src.infra.database.models.tdee_calculation import TdeeCalculation

def view_all_users():
    """Display all users with their profile information."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mealtrack.db')
    engine = create_engine(f'sqlite:///{db_path}')
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    print("📊 All Users in Database")
    print("=" * 100)
    print(f"{'#':<3} {'Username':<20} {'Email':<35} {'Profile ID':<38} {'Age':<5} {'Goal':<12}")
    print("-" * 100)
    
    users = session.query(User).all()
    
    for i, user in enumerate(users, 1):
        # Get current profile
        profile = session.query(UserProfile).filter(
            UserProfile.user_id == user.id,
            UserProfile.is_current == True
        ).first()
        
        # Get current goal
        goal = session.query(UserGoal).filter(
            UserGoal.user_id == user.id,
            UserGoal.is_current == True
        ).first()
        
        if profile and goal:
            print(f"{i:<3} {user.username:<20} {user.email:<35} {profile.id:<38} {profile.age:<5} {goal.fitness_goal:<12}")
    
    print("\n" + "=" * 100)
    print(f"Total Users: {len(users)}")
    
    # Show detailed info for first 3 users
    print("\n📋 Detailed Info for First 3 Users:")
    print("=" * 100)
    
    for user in users[:3]:
        profile = session.query(UserProfile).filter(
            UserProfile.user_id == user.id,
            UserProfile.is_current == True
        ).first()
        
        goal = session.query(UserGoal).filter(
            UserGoal.user_id == user.id,
            UserGoal.is_current == True
        ).first()
        
        preference = session.query(UserPreference).filter(
            UserPreference.user_id == user.id
        ).first()
        
        latest_tdee = session.query(TdeeCalculation).filter(
            TdeeCalculation.user_id == user.id
        ).order_by(TdeeCalculation.calculation_date.desc()).first()
        
        print(f"\n👤 {user.username}")
        print(f"   Profile ID: {profile.id if profile else 'N/A'}")
        
        if profile:
            print(f"   Physical: {profile.age}yo, {profile.gender}, {profile.height_cm}cm, {profile.weight_kg}kg")
        
        if goal:
            print(f"   Goal: {goal.fitness_goal} | Activity: {goal.activity_level}")
            print(f"   Meals: {goal.meals_per_day}/day | Snacks: {goal.snacks_per_day}/day")
        
        if preference:
            dietary = [dp.preference for dp in preference.dietary_preferences]
            allergies = [a.allergen for a in preference.allergies]
            if dietary:
                print(f"   Dietary: {', '.join(dietary)}")
            if allergies:
                print(f"   Allergies: {', '.join(allergies)}")
        
        if latest_tdee:
            print(f"   TDEE: {latest_tdee.tdee:.0f} cal | "
                  f"Macros: P:{latest_tdee.protein_grams:.0f}g, "
                  f"C:{latest_tdee.carbs_grams:.0f}g, "
                  f"F:{latest_tdee.fat_grams:.0f}g")
        
        print(f"   Test URL: http://localhost:8000/v2/daily-meals/suggestions/{profile.id}")
    
    session.close()


def view_profile_ids_only():
    """Quick view of just profile IDs for testing."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mealtrack.db')
    engine = create_engine(f'sqlite:///{db_path}')
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    print("\n🔑 Quick Profile ID List:")
    print("=" * 60)
    
    profiles = session.query(UserProfile).filter(
        UserProfile.is_current == True
    ).limit(10).all()
    
    for i, profile in enumerate(profiles, 1):
        user = session.query(User).filter(User.id == profile.user_id).first()
        print(f"{i}. {profile.id} ({user.username if user else 'Unknown'})")
    
    session.close()


if __name__ == "__main__":
    view_all_users()
    view_profile_ids_only()