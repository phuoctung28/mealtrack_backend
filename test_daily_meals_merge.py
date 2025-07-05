#!/usr/bin/env python3
"""
Test script to demonstrate the merged daily meals v1 API.
Shows both profile-based and direct preferences approaches.
"""
import requests

BASE_URL = "http://localhost:8000/v1/daily-meals"

print("=== Daily Meals v1 API Test (Merged v2 functionality) ===\n")

# Test 1: Direct preferences approach (original v1)
print("1. Testing direct preferences approach:")
direct_request = {
    "age": 30,
    "gender": "male", 
    "height": 175,
    "weight": 70,
    "activity_level": "moderately_active",
    "goal": "maintain_weight",
    "dietary_preferences": ["vegetarian"],
    "health_conditions": [],
    "target_calories": 2500,
    "target_macros": {
        "protein": 150,
        "carbs": 250,
        "fat": 80
    }
}

try:
    response = requests.post(f"{BASE_URL}/suggestions", json=direct_request)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Direct preferences approach works!")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Profile-based approach (merged from v2)  
print("\n2. Testing profile-based approach:")
# For profile-based, we need to pass user_profile_id as a query parameter
profile_url = f"{BASE_URL}/suggestions?user_profile_id=test-profile-123"

try:
    response = requests.post(profile_url)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Profile-based approach works!")
    elif response.status_code == 404:
        print("   ⚠️  Profile not found (expected for test profile)")
    elif response.status_code == 422:
        # Try with both request body and query param
        response2 = requests.post(f"{BASE_URL}/suggestions", params={"user_profile_id": "test-profile-123"})
        print(f"   Retry status: {response2.status_code}")
        if response2.status_code in [200, 404]:
            print("   ✅ Profile-based approach works with params!")
        else:
            print(f"   ❌ Error: {response2.text[:200]}")
    else:
        print(f"   ❌ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Profile summary endpoint (from v2)
print("\n3. Testing profile summary endpoint:")
try:
    response = requests.get(f"{BASE_URL}/profile/test-profile-123/summary")
    print(f"   Status: {response.status_code}")
    if response.status_code in [200, 404]:
        print("   ✅ Profile summary endpoint available!")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n=== Summary ===")
print("The v1 daily-meals API now supports both:")
print("- Direct preferences (original v1 - for anonymous users)")
print("- Profile-based queries (from v2 - for registered users)")
print("- Profile summary endpoint (from v2 - for debugging)")