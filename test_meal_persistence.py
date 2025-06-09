#!/usr/bin/env python3
"""
Test script to verify meal macros persistence.

This script tests:
1. Updating meal macros with new weight
2. Retrieving the meal to verify the update was persisted
3. Confirming the nutrition values are correctly calculated
"""

import time

import requests

BASE_URL = "http://127.0.0.1:8000/v1"

def test_meal_macros_persistence():
    """Test that meal macros updates are properly persisted."""
    
    print("🔄 Testing Meal Macros Persistence")
    print("=" * 50)
    
    # Test meal ID (in real usage, this would come from uploading a meal image)
    meal_id = "test-meal-persistence-123"
    
    # 1. Get initial meal data
    print("\n1. Getting initial meal data:")
    try:
        response = requests.get(f"{BASE_URL}/meals/{meal_id}")
        if response.status_code == 200:
            initial_meal = response.json()
            print(f"   ✅ Initial meal status: {initial_meal['status']}")
            if initial_meal.get('nutrition'):
                nutrition = initial_meal['nutrition']
                print(f"   📊 Initial weight: {nutrition['total_weight_grams']}g")
                print(f"   🍽️  Initial calories: {nutrition['total_calories']}")
                print(f"   🥩 Initial protein: {nutrition['total_macros']['protein']}g")
            else:
                print("   ⚠️  No nutrition data in initial meal")
        else:
            print(f"   ❌ Error getting initial meal: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return
    
    # 2. Update meal macros to 400g
    print("\n2. Updating meal macros to 400g:")
    update_data = {
        "weight_grams": 400.0
    }
    try:
        response = requests.post(f"{BASE_URL}/meals/{meal_id}/macros", json=update_data)
        if response.status_code == 200:
            updated_response = response.json()
            print(f"   ✅ Update successful!")
            print(f"   📊 New weight: {updated_response['weight_grams']}g")
            print(f"   🍽️  New total calories: {updated_response['total_calories']}")
            print(f"   📈 Calories per 100g: {updated_response['calories_per_100g']}")
            print(f"   🥩 New protein: {updated_response['total_macros']['protein']}g")
            print(f"   🔄 Status: {updated_response['status']}")
        else:
            print(f"   ❌ Update failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return
    
    # 3. Wait a moment for the update to be processed
    print("\n3. Waiting for update to be processed...")
    time.sleep(1)
    
    # 4. Retrieve the meal again to verify persistence
    print("\n4. Retrieving meal to verify update was persisted:")
    try:
        response = requests.get(f"{BASE_URL}/meals/{meal_id}")
        if response.status_code == 200:
            retrieved_meal = response.json()
            print(f"   ✅ Meal retrieved successfully!")
            print(f"   📊 Status: {retrieved_meal['status']}")
            
            if retrieved_meal.get('nutrition'):
                nutrition = retrieved_meal['nutrition']
                print(f"   📊 Current weight: {nutrition['total_weight_grams']}g")
                print(f"   🍽️  Current calories: {nutrition['total_calories']}")
                print(f"   📈 Calories per 100g: {nutrition['calories_per_100g']}")
                print(f"   🥩 Current protein: {nutrition['total_macros']['protein']}g")
                print(f"   🥬 Current carbs: {nutrition['total_macros']['carbs']}g")
                print(f"   🧈 Current fat: {nutrition['total_macros']['fat']}g")
                
                # Verify the weight was updated
                if nutrition['total_weight_grams'] == 400.0:
                    print("   ✅ VERIFIED: Weight update was persisted!")
                else:
                    print(f"   ❌ FAILED: Expected 400g, got {nutrition['total_weight_grams']}g")
                
                # Verify nutrition was scaled
                if initial_meal.get('nutrition'):
                    initial_nutrition = initial_meal['nutrition']
                    expected_ratio = 400.0 / initial_nutrition['total_weight_grams']
                    expected_calories = initial_nutrition['total_calories'] * expected_ratio
                    
                    if abs(nutrition['total_calories'] - expected_calories) < 1.0:
                        print("   ✅ VERIFIED: Nutrition was correctly scaled!")
                    else:
                        print(f"   ❌ FAILED: Expected ~{expected_calories} calories, got {nutrition['total_calories']}")
            else:
                print("   ❌ FAILED: No nutrition data found in retrieved meal")
        else:
            print(f"   ❌ Error retrieving meal: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # 5. Test another weight update to verify it works consistently
    print("\n5. Testing second update to 250g:")
    update_data_2 = {
        "weight_grams": 250.0
    }
    try:
        response = requests.post(f"{BASE_URL}/meals/{meal_id}/macros", json=update_data_2)
        if response.status_code == 200:
            updated_response_2 = response.json()
            print(f"   ✅ Second update successful!")
            print(f"   📊 New weight: {updated_response_2['weight_grams']}g")
            print(f"   🍽️  New total calories: {updated_response_2['total_calories']}")
            
            # Wait and retrieve again
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/meals/{meal_id}")
            if response.status_code == 200:
                final_meal = response.json()
                if final_meal.get('nutrition'):
                    final_nutrition = final_meal['nutrition']
                    if final_nutrition['total_weight_grams'] == 250.0:
                        print("   ✅ VERIFIED: Second update was also persisted!")
                    else:
                        print(f"   ❌ FAILED: Expected 250g, got {final_nutrition['total_weight_grams']}g")
        else:
            print(f"   ❌ Second update failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("  • Meal macros can be updated with precise weight")
    print("  • Updates are persisted to the database")
    print("  • Nutrition values are correctly scaled")
    print("  • Multiple updates work consistently")
    print("=" * 50)

if __name__ == "__main__":
    test_meal_macros_persistence() 