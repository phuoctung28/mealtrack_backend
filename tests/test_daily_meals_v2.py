#!/usr/bin/env python3
"""
Test script for Daily Meal Suggestions V2 API using user_profile_id

This script demonstrates how to use the new endpoints that fetch
all user data automatically based on user_profile_id.
"""

import requests
import json
from typing import Dict

# API Base URL
BASE_URL = "http://localhost:8000"


def create_test_user_data():
    """Create test user data in the database."""
    print("🔧 Creating test user data...")
    
    # First save onboarding data
    onboarding_data = {
        "age": 28,
        "gender": "male",
        "height": 175,
        "weight": 75,
        "body_fat_percentage": 15,
        "activity_level": "moderate",
        "goal": "maintenance",
        "target_weight": 75,
        "dietary_preferences": ["vegetarian", "high_protein"],
        "health_conditions": [],
        "allergies": ["nuts"],
        "meals_per_day": 3,
        "snacks_per_day": 2
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/user-onboarding/save",
        json=onboarding_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Test user created successfully!")
        print(f"   User ID: {data['user_id']}")
        print(f"   Profile ID: {data['profile_id']}")
        print(f"   TDEE: {data['tdee_calculation']['tdee']}")
        print(f"   Macros: P:{data['tdee_calculation']['macros']['protein']}g, "
              f"C:{data['tdee_calculation']['macros']['carbs']}g, "
              f"F:{data['tdee_calculation']['macros']['fat']}g")
        return data['profile_id']
    else:
        print(f"❌ Error creating test user: {response.status_code}")
        print(response.json())
        return None


def test_meal_suggestions_by_profile(profile_id: str):
    """Test getting meal suggestions using profile ID."""
    print(f"\n🍽️  Testing Daily Meal Suggestions with Profile ID: {profile_id}")
    print("=" * 60)
    
    # Test 1: Get summary of data that will be used
    print("\n📊 Test 1: Getting meal planning data summary...")
    response = requests.get(f"{BASE_URL}/v2/daily-meals/profile/{profile_id}/summary")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Profile data retrieved successfully!")
        print(f"\nProfile Info:")
        print(f"  Age: {data['profile']['age']}")
        print(f"  Gender: {data['profile']['gender']}")
        print(f"  Height: {data['profile']['height_cm']}cm")
        print(f"  Weight: {data['profile']['weight_kg']}kg")
        
        if data['goal']:
            print(f"\nGoal Info:")
            print(f"  Activity Level: {data['goal']['activity_level']}")
            print(f"  Fitness Goal: {data['goal']['fitness_goal']}")
            print(f"  Meals per Day: {data['goal']['meals_per_day']}")
        
        if data['preferences']['dietary']:
            print(f"\nDietary Preferences: {', '.join(data['preferences']['dietary'])}")
        
        if data['preferences']['allergies']:
            print(f"Allergies: {', '.join(data['preferences']['allergies'])}")
        
        if data['latest_tdee']:
            print(f"\nTDEE Calculation:")
            print(f"  BMR: {data['latest_tdee']['bmr']}")
            print(f"  TDEE: {data['latest_tdee']['tdee']}")
            print(f"  Target Calories: {data['latest_tdee']['target_calories']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
    
    # Test 2: Get full day meal suggestions
    print("\n\n📅 Test 2: Getting daily meal suggestions...")
    response = requests.post(f"{BASE_URL}/v2/daily-meals/suggestions/{profile_id}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Generated {data['meal_count']} meals")
        
        print(f"\n📊 Daily Totals:")
        print(f"  Calories: {data['daily_totals']['calories']:.0f} / {data['target_totals']['calories']:.0f}")
        print(f"  Protein: {data['daily_totals']['protein']:.1f}g / {data['target_totals']['protein']:.1f}g")
        print(f"  Carbs: {data['daily_totals']['carbs']:.1f}g / {data['target_totals']['carbs']:.1f}g")
        print(f"  Fat: {data['daily_totals']['fat']:.1f}g / {data['target_totals']['fat']:.1f}g")
        
        print("\n🍴 Suggested Meals:")
        for meal in data['meals']:
            print(f"\n  {meal['meal_type'].upper()}: {meal['name']}")
            print(f"    📝 {meal['description']}")
            print(f"    ⏱️  {meal['total_time']} min | 🔥 {meal['calories']} cal")
            print(f"    💪 P: {meal['protein']}g | C: {meal['carbs']}g | F: {meal['fat']}g")
            
            # Check dietary flags
            flags = []
            if meal.get('is_vegetarian'):
                flags.append("🌱 Vegetarian")
            if meal.get('is_vegan'):
                flags.append("🌿 Vegan")
            if meal.get('is_gluten_free'):
                flags.append("🌾 Gluten-Free")
            if flags:
                print(f"    {' | '.join(flags)}")
            
            # Check for allergens
            if 'ingredients' in meal:
                has_nuts = any('nut' in ing.lower() or 'almond' in ing.lower() 
                              for ing in meal['ingredients'])
                if has_nuts:
                    print("    ⚠️  Contains nuts")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
    
    # Test 3: Get single meal suggestion
    print("\n\n🥞 Test 3: Getting single breakfast suggestion...")
    response = requests.post(f"{BASE_URL}/v2/daily-meals/suggestions/{profile_id}/breakfast")
    
    if response.status_code == 200:
        data = response.json()
        meal = data['meal']
        print(f"✅ Success! Generated breakfast suggestion")
        print(f"\n  {meal['name']}")
        print(f"  📝 {meal['description']}")
        print(f"  ⏱️  Prep: {meal['prep_time']}min | Cook: {meal['cook_time']}min")
        print(f"  🔥 {meal['calories']} calories")
        print(f"\n  🥘 Ingredients:")
        for ingredient in meal['ingredients'][:5]:  # Show first 5
            print(f"    • {ingredient}")
        if len(meal['ingredients']) > 5:
            print(f"    ... and {len(meal['ingredients']) - 5} more")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.json())


def test_different_profiles():
    """Test with different user profiles to show variety."""
    print("\n\n🧪 Testing with Different User Profiles")
    print("=" * 60)
    
    profiles = [
        {
            "name": "Active Female - Weight Loss",
            "data": {
                "age": 25,
                "gender": "female",
                "height": 165,
                "weight": 70,
                "activity_level": "active",
                "goal": "cutting",
                "dietary_preferences": ["gluten_free", "dairy_free"],
                "health_conditions": [],
                "meals_per_day": 4,
                "snacks_per_day": 1
            }
        },
        {
            "name": "Sedentary Male - Muscle Gain",
            "data": {
                "age": 35,
                "gender": "male",
                "height": 180,
                "weight": 85,
                "activity_level": "sedentary",
                "goal": "bulking",
                "dietary_preferences": ["high_protein"],
                "health_conditions": ["diabetes"],
                "meals_per_day": 5,
                "snacks_per_day": 2
            }
        }
    ]
    
    for profile_info in profiles:
        print(f"\n\n👤 Profile: {profile_info['name']}")
        print("-" * 40)
        
        # Create profile
        response = requests.post(
            f"{BASE_URL}/v1/user-onboarding/save",
            json=profile_info['data']
        )
        
        if response.status_code == 200:
            data = response.json()
            profile_id = data['profile_id']
            
            print(f"Profile created: {profile_id}")
            print(f"TDEE: {data['tdee_calculation']['tdee']:.0f} calories")
            print(f"Macros: P:{data['tdee_calculation']['macros']['protein']:.0f}g, "
                  f"C:{data['tdee_calculation']['macros']['carbs']:.0f}g, "
                  f"F:{data['tdee_calculation']['macros']['fat']:.0f}g")
            
            # Get one meal suggestion
            response = requests.post(f"{BASE_URL}/v2/daily-meals/suggestions/{profile_id}/lunch")
            if response.status_code == 200:
                meal = response.json()['meal']
                print(f"\nSample Lunch: {meal['name']}")
                print(f"  Calories: {meal['calories']} | "
                      f"P: {meal['protein']}g | C: {meal['carbs']}g | F: {meal['fat']}g")


if __name__ == "__main__":
    print("🚀 Daily Meal Suggestions V2 API Test")
    print("Make sure the API server is running at http://localhost:8000")
    print("\n")
    
    try:
        # Check if API is running
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print("❌ API server is not responding. Please start the server first.")
            exit(1)
        
        # Create test user and get profile ID
        profile_id = create_test_user_data()
        
        if profile_id:
            # Test meal suggestions
            test_meal_suggestions_by_profile(profile_id)
            
            # Test with different profiles
            test_different_profiles()
            
            print("\n\n✅ All tests completed!")
            print("\n📝 Summary of V2 API:")
            print("- Endpoints accept user_profile_id instead of full user data")
            print("- All user information is fetched from the database automatically")
            print("- TDEE is calculated if not already stored")
            print("- Dietary preferences and allergies are respected")
            print("- Profile summary endpoint helps debug what data is being used")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server at http://localhost:8000")
        print("Please make sure the server is running: uvicorn api.main:app --reload")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")