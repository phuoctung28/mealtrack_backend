#!/usr/bin/env python3
"""
Quick script to create a few test users and display their profile IDs for immediate testing.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infra.database.config import SessionLocal, SQLALCHEMY_DATABASE_URL
from populate_mock_data import MockDataGenerator


def create_quick_test_users():
    """Create 3 test users quickly."""
    session = SessionLocal()
    
    print("🚀 Creating Quick Test Users")
    print("=" * 60)
    print(f"Database Type: MySQL")
    print(f"Database URL: {SQLALCHEMY_DATABASE_URL.split('@')[1] if '@' in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL}")
    print()
    
    generator = MockDataGenerator(session)
    
    # Create 3 specific user profiles
    test_profiles = [
        {
            "name": "Test User 1 - Vegetarian",
            "age": 25,
            "gender": "female",
            "height_cm": 165,
            "weight_kg": 60,
            "body_fat_percentage": 22,
            "activity_level": "moderate",
            "fitness_goal": "maintenance",
            "dietary_preferences": ["vegetarian", "high_protein"],
            "health_conditions": [],
            "allergies": ["nuts"]
        },
        {
            "name": "Test User 2 - Weight Loss",
            "age": 35,
            "gender": "male",
            "height_cm": 180,
            "weight_kg": 90,
            "body_fat_percentage": 25,
            "activity_level": "light",
            "fitness_goal": "cutting",
            "dietary_preferences": ["low_carb"],
            "health_conditions": ["diabetes"],
            "allergies": []
        },
        {
            "name": "Test User 3 - Muscle Building",
            "age": 28,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 70,
            "body_fat_percentage": 15,
            "activity_level": "active",
            "fitness_goal": "bulking",
            "dietary_preferences": ["high_protein"],
            "health_conditions": [],
            "allergies": ["shellfish", "dairy"]
        }
    ]
    
    created_users = []
    for profile in test_profiles:
        user = generator.create_user(profile)
        created_users.append(user)
    
    session.commit()
    
    print("\n✅ Test Users Created Successfully!")
    print("\n" + "=" * 60)
    print("🔑 PROFILE IDs FOR TESTING:")
    print("=" * 60)
    
    from src.infra.database.models.user.profile import UserProfile
    
    for i, user in enumerate(created_users):
        profile = session.query(UserProfile).filter(
            UserProfile.user_id == user.id,
            UserProfile.is_current == True
        ).first()
        
        if profile:
            print(f"\n{i+1}. {user.username}")
            print(f"   Profile ID: {profile.id}")
            print(f"   Details: {test_profiles[i]['name']}")
            print(f"   Test URL: http://localhost:8000/v2/daily-meals/suggestions/{profile.id}")
    
    print("\n" + "=" * 60)
    print("📝 Example API Calls:")
    print("=" * 60)
    
    first_profile_id = session.query(UserProfile).filter(
        UserProfile.user_id == created_users[0].id,
        UserProfile.is_current == True
    ).first().id
    
    print(f"""
# Get daily meal suggestions
curl -X POST http://localhost:8000/v2/daily-meals/suggestions/{first_profile_id}

# Get single breakfast suggestion
curl -X POST http://localhost:8000/v2/daily-meals/suggestions/{first_profile_id}/breakfast

# Get meal planning data summary
curl http://localhost:8000/v2/daily-meals/profile/{first_profile_id}/summary
""")
    
    session.close()


if __name__ == "__main__":
    create_quick_test_users()