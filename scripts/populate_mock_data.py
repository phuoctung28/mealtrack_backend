#!/usr/bin/env python3
"""
Populate database with mock data for testing and development.

This script creates:
- Multiple users with different profiles
- User preferences (dietary, health conditions, allergies)
- User goals with various fitness objectives
- TDEE calculations
- Meal plans and conversations
"""

import os
import random
import sys
from datetime import datetime, timedelta
from typing import Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infra.database.config import SessionLocal, SQLALCHEMY_DATABASE_URL
from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile
# Removed models are now part of UserProfile
from src.infra.database.models.meal_planning.meal_plan import MealPlan
from src.infra.database.models.conversation.conversation import Conversation
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.model.tdee import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem

# Mock data templates
FIRST_NAMES = ["John", "Jane", "Michael", "Sarah", "David", "Emma", "James", "Lisa", "Robert", "Maria"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

DIETARY_PREFERENCES = ["vegetarian", "vegan", "gluten_free", "dairy_free", "keto", "paleo", "low_carb", "high_protein"]
HEALTH_CONDITIONS = ["diabetes", "hypertension", "high_cholesterol", "celiac_disease", "lactose_intolerance"]
ALLERGIES = ["nuts", "peanuts", "shellfish", "eggs", "soy", "wheat", "dairy", "fish"]

USER_PROFILES = [
    {
        "name": "Active Young Male",
        "age": 25,
        "gender": "male",
        "height_cm": 180,
        "weight_kg": 75,
        "body_fat_percentage": 12,
        "activity_level": "active",
        "fitness_goal": "bulking",
        "dietary_preferences": ["high_protein"],
        "health_conditions": [],
        "allergies": []
    },
    {
        "name": "Sedentary Office Worker",
        "age": 35,
        "gender": "female",
        "height_cm": 165,
        "weight_kg": 70,
        "body_fat_percentage": 28,
        "activity_level": "sedentary",
        "fitness_goal": "cutting",
        "dietary_preferences": ["low_carb", "gluten_free"],
        "health_conditions": ["diabetes"],
        "allergies": ["nuts"]
    },
    {
        "name": "Fitness Enthusiast",
        "age": 28,
        "gender": "male",
        "height_cm": 175,
        "weight_kg": 80,
        "body_fat_percentage": 15,
        "activity_level": "extra",
        "fitness_goal": "maintenance",
        "dietary_preferences": ["vegetarian", "high_protein"],
        "health_conditions": [],
        "allergies": ["shellfish", "peanuts"]
    },
    {
        "name": "Weight Loss Journey",
        "age": 42,
        "gender": "female",
        "height_cm": 160,
        "weight_kg": 85,
        "body_fat_percentage": 35,
        "activity_level": "light",
        "fitness_goal": "cutting",
        "dietary_preferences": ["dairy_free", "low_carb"],
        "health_conditions": ["hypertension", "high_cholesterol"],
        "allergies": ["dairy", "eggs"]
    },
    {
        "name": "Vegan Athlete",
        "age": 30,
        "gender": "male",
        "height_cm": 185,
        "weight_kg": 82,
        "body_fat_percentage": 10,
        "activity_level": "extra",
        "fitness_goal": "bulking",
        "dietary_preferences": ["vegan", "high_protein", "gluten_free"],
        "health_conditions": [],
        "allergies": []
    },
    {
        "name": "Moderate Activity Mom",
        "age": 38,
        "gender": "female",
        "height_cm": 168,
        "weight_kg": 65,
        "body_fat_percentage": 25,
        "activity_level": "moderate",
        "fitness_goal": "maintenance",
        "dietary_preferences": ["paleo"],
        "health_conditions": ["lactose_intolerance"],
        "allergies": ["soy"]
    },
    {
        "name": "Senior Fitness",
        "age": 55,
        "gender": "male",
        "height_cm": 172,
        "weight_kg": 78,
        "body_fat_percentage": 22,
        "activity_level": "light",
        "fitness_goal": "maintenance",
        "dietary_preferences": ["low_carb"],
        "health_conditions": ["diabetes", "hypertension"],
        "allergies": ["wheat"]
    },
    {
        "name": "Young Professional",
        "age": 26,
        "gender": "female",
        "height_cm": 170,
        "weight_kg": 58,
        "body_fat_percentage": 20,
        "activity_level": "moderate",
        "fitness_goal": "maintenance",
        "dietary_preferences": ["vegetarian", "dairy_free"],
        "health_conditions": [],
        "allergies": ["nuts", "eggs"]
    },
    {
        "name": "Bodybuilder",
        "age": 32,
        "gender": "male",
        "height_cm": 188,
        "weight_kg": 95,
        "body_fat_percentage": 8,
        "activity_level": "extra",
        "fitness_goal": "bulking",
        "dietary_preferences": ["high_protein", "keto"],
        "health_conditions": [],
        "allergies": []
    },
    {
        "name": "Casual Gym Goer",
        "age": 29,
        "gender": "female",
        "height_cm": 163,
        "weight_kg": 62,
        "body_fat_percentage": 24,
        "activity_level": "moderate",
        "fitness_goal": "cutting",
        "dietary_preferences": ["gluten_free"],
        "health_conditions": ["celiac_disease"],
        "allergies": ["wheat", "shellfish"]
    }
]


class MockDataGenerator:
    def __init__(self, session):
        self.session = session
        self.tdee_service = TdeeCalculationService()
        self.created_users = []
        
    def generate_email(self, first_name: str, last_name: str) -> str:
        """Generate unique email."""
        random_num = random.randint(100, 999)
        return f"{first_name.lower()}.{last_name.lower()}{random_num}@example.com"
    
    def generate_username(self, first_name: str, last_name: str) -> str:
        """Generate unique username."""
        random_num = random.randint(100, 999)
        return f"{first_name.lower()}_{last_name.lower()}{random_num}"
    
    def create_user(self, profile_template: Dict) -> User:
        """Create a user with profile, preferences, and goals."""
        # Generate user info
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        email = self.generate_email(first_name, last_name)
        username = self.generate_username(first_name, last_name)
        
        # Create user
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password_hash="hashed_password_123",  # In real app, use proper hashing
            is_active=True
        )
        self.session.add(user)
        self.session.flush()
        
        # Create profile
        profile = UserProfile(
            user_id=user.id,
            age=profile_template["age"],
            gender=profile_template["gender"],
            height_cm=profile_template["height_cm"],
            weight_kg=profile_template["weight_kg"],
            body_fat_percentage=profile_template.get("body_fat_percentage"),
            is_current=True
        )
        self.session.add(profile)
        self.session.flush()
        
        # Update profile with all data including goals and preferences
        meals_per_day = random.choice([3, 4, 5])
        snacks_per_day = random.choice([0, 1, 2])
        
        profile.activity_level = profile_template["activity_level"]
        profile.fitness_goal = profile_template["fitness_goal"]
        profile.target_weight_kg = profile_template["weight_kg"] + random.randint(-5, 5)
        profile.meals_per_day = meals_per_day
        profile.snacks_per_day = snacks_per_day
        profile.dietary_preferences = profile_template.get("dietary_preferences", [])
        profile.health_conditions = profile_template.get("health_conditions", [])
        profile.allergies = profile_template.get("allergies", [])
        self.session.flush()
        
        # Calculate TDEE (no longer saved to DB)
        self.calculate_tdee_for_profile(user, profile)
        
        # Create some historical data
        self.create_historical_data(user, profile)
        
        self.session.commit()
        
        print(f"✅ Created user: {username} ({profile_template['name']})")
        return user
    
    def calculate_tdee_for_profile(self, user: User, profile: UserProfile):
        """Calculate TDEE for profile (no longer saved to DB)."""
        # Map to domain enums
        sex = Sex.MALE if profile.gender == "male" else Sex.FEMALE
        
        activity_map = {
            "sedentary": ActivityLevel.SEDENTARY,
            "light": ActivityLevel.LIGHT,
            "moderate": ActivityLevel.MODERATE,
            "active": ActivityLevel.ACTIVE,
            "extra": ActivityLevel.EXTRA
        }
        
        goal_map = {
            "maintenance": Goal.MAINTENANCE,
            "cutting": Goal.CUTTING,
            "bulking": Goal.BULKING
        }
        
        # Create TDEE request
        tdee_request = TdeeRequest(
            age=profile.age,
            sex=sex,
            height=profile.height_cm,
            weight=profile.weight_kg,
            body_fat_pct=profile.body_fat_percentage,
            activity_level=activity_map[profile.activity_level],
            goal=goal_map[profile.fitness_goal],
            unit_system=UnitSystem.METRIC
        )
        
        # Calculate TDEE
        tdee_result = self.tdee_service.calculate_tdee(tdee_request)
        
        # Log the calculation result
        print(f"  - BMR: {tdee_result.bmr:.0f}, TDEE: {tdee_result.tdee:.0f}")
        print(f"  - Macros - Protein: {tdee_result.macros.protein:.0f}g, Carbs: {tdee_result.macros.carbs:.0f}g, Fat: {tdee_result.macros.fat:.0f}g")
    
    def create_historical_data(self, user: User, current_profile: UserProfile):
        """Create some historical weight data."""
        # Create 3-5 historical profiles (weight changes)
        num_historical = random.randint(3, 5)
        
        for i in range(num_historical):
            days_ago = (i + 1) * 30  # Monthly snapshots
            historical_date = datetime.now() - timedelta(days=days_ago)
            
            # Create historical profile (weight progression)
            weight_change = random.uniform(-2, 2)  # +/- 2kg per month
            historical_weight = current_profile.weight_kg + (weight_change * (i + 1))
            
            hist_profile = UserProfile(
                user_id=user.id,
                age=current_profile.age,
                gender=current_profile.gender,
                height_cm=current_profile.height_cm,
                weight_kg=historical_weight,
                body_fat_percentage=current_profile.body_fat_percentage,
                activity_level=current_profile.activity_level,
                fitness_goal=current_profile.fitness_goal,
                target_weight_kg=current_profile.target_weight_kg,
                meals_per_day=current_profile.meals_per_day,
                snacks_per_day=current_profile.snacks_per_day,
                dietary_preferences=current_profile.dietary_preferences,
                health_conditions=current_profile.health_conditions,
                allergies=current_profile.allergies,
                is_current=False,
                created_at=historical_date,
                updated_at=historical_date
            )
            self.session.add(hist_profile)
    
    def create_meal_plans_and_conversations(self):
        """Create some meal plans and conversations for users."""
        for user in self.created_users[:5]:  # Create for first 5 users
            # Create a meal plan
            meal_plan = MealPlan(
                user_id=user.id,
                dietary_preferences=["vegetarian"] if random.random() > 0.5 else [],
                allergies=[],
                fitness_goal="muscle_gain" if random.random() > 0.5 else "weight_loss",
                meals_per_day=3,
                snacks_per_day=1,
                plan_duration="weekly"
            )
            self.session.add(meal_plan)
            
            # Create a conversation
            conversation = Conversation(
                user_id=user.id,
                state="completed",
                context={
                    "preferences_collected": True,
                    "plan_generated": True
                }
            )
            self.session.add(conversation)
        
        self.session.commit()
        print(f"✅ Created meal plans and conversations for 5 users")
    
    def generate_all_data(self):
        """Generate all mock data."""
        print("🚀 Starting mock data generation...")
        print("=" * 60)
        
        # Create users from templates
        for template in USER_PROFILES:
            user = self.create_user(template)
            self.created_users.append(user)
        
        # Create additional random users
        print("\n📊 Creating additional random users...")
        for i in range(10):
            # Randomly modify a template
            template = USER_PROFILES[i % len(USER_PROFILES)].copy()
            template["age"] = random.randint(18, 65)
            template["weight_kg"] = random.randint(50, 100)
            template["height_cm"] = random.randint(150, 195)
            template["dietary_preferences"] = random.sample(DIETARY_PREFERENCES, k=random.randint(0, 3))
            template["health_conditions"] = random.sample(HEALTH_CONDITIONS, k=random.randint(0, 2))
            template["allergies"] = random.sample(ALLERGIES, k=random.randint(0, 2))
            
            user = self.create_user(template)
            self.created_users.append(user)
        
        # Create meal plans and conversations
        self.create_meal_plans_and_conversations()
        
        print(f"\n✅ Successfully created {len(self.created_users)} users with complete profiles!")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary of created data."""
        print("\n📊 Mock Data Summary")
        print("=" * 60)
        
        # Count statistics
        total_profiles = self.session.query(UserProfile).count()
        
        print(f"Total Users: {len(self.created_users)}")
        print(f"Total Profiles: {total_profiles}")
        
        print("\n📝 Sample Users Created:")
        for i, user in enumerate(self.created_users[:5]):
            profile = self.session.query(UserProfile).filter(
                UserProfile.user_id == user.id,
                UserProfile.is_current == True
            ).first()
            
            if profile:
                print(f"\n{i+1}. {user.username}")
                print(f"   Email: {user.email}")
                print(f"   Profile ID: {profile.id}")
                print(f"   Age: {profile.age}, Gender: {profile.gender}")
                print(f"   Height: {profile.height_cm}cm, Weight: {profile.weight_kg}kg")
                print(f"   Activity: {profile.activity_level}, Goal: {profile.fitness_goal}")
                if profile.dietary_preferences:
                    print(f"   Dietary Preferences: {', '.join(profile.dietary_preferences)}")


def main():
    """Main function."""
    print("🗄️  MealTrack Mock Data Generator")
    print("=" * 60)
    print(f"Database Type: MySQL")
    print(f"Database URL: {SQLALCHEMY_DATABASE_URL.split('@')[1] if '@' in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL}")
    print()
    
    # Create database session
    session = SessionLocal()
    
    try:
        # Check if users already exist
        existing_users = session.query(User).count()
        if existing_users > 0:
            response = input(f"\n⚠️  Found {existing_users} existing users. Continue and add more? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Cancelled.")
                return
        
        # Generate mock data
        generator = MockDataGenerator(session)
        generator.generate_all_data()
        
        print("\n✨ Mock data generation complete!")
        print("\nYou can now test the API with these user profiles.")
        print("Use the profile IDs shown above with the V2 endpoints.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    main()