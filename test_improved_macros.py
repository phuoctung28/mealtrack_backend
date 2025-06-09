#!/usr/bin/env python3
"""
Test script for improved macro endpoints with gram-based measurements.

This script demonstrates:
1. Getting meal macros with specific weight
2. Updating meal macros with gram-based portion
3. Tracking consumed macros from meals
"""

import requests

BASE_URL = "http://127.0.0.1:8000/v1"

def test_meal_macros_api():
    """Test the improved macro endpoints."""
    
    print("🍽️  Testing Improved Macro Endpoints with Gram-based Measurements")
    print("=" * 70)
    
    # Test meal ID (in real usage, this would come from uploading a meal image)
    meal_id = "test-meal-123"
    
    # 1. Get meal macros for default portion
    print("\n1. Getting meal macros (default portion):")
    try:
        response = requests.get(f"{BASE_URL}/macros/meal/{meal_id}")
        if response.status_code == 200:
            meal_data = response.json()
            print(f"   ✅ Meal: {meal_data['name']}")
            print(f"   📊 Total: {meal_data['total_calories']} cal, {meal_data['total_weight_grams']}g")
            print(f"   📈 Per 100g: {meal_data['calories_per_100g']} cal")
            print(f"   🥩 Macros/100g: P{meal_data['macros_per_100g']['protein']}g C{meal_data['macros_per_100g']['carbs']}g F{meal_data['macros_per_100g']['fat']}g")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # 2. Get meal macros for specific weight (200g portion)
    print("\n2. Getting meal macros for 200g portion:")
    try:
        response = requests.get(f"{BASE_URL}/macros/meal/{meal_id}?weight_grams=200")
        if response.status_code == 200:
            scaled_data = response.json()
            print(f"   ✅ Scaled to: {scaled_data['actual_weight_grams']}g")
            print(f"   📊 Adjusted: {scaled_data['actual_calories']} cal")
            print(f"   🥩 Macros: P{scaled_data['actual_macros']['protein']}g C{scaled_data['actual_macros']['carbs']}g F{scaled_data['actual_macros']['fat']}g")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # 3. Update meal macros with specific weight
    print("\n3. Updating meal macros to 280g:")
    update_data = {
        "weight_grams": 280.0
    }
    try:
        response = requests.post(f"{BASE_URL}/meals/{meal_id}/macros", json=update_data)
        if response.status_code == 200:
            updated_meal = response.json()
            print(f"   ✅ Updated meal weight: {updated_meal['weight_grams']}g")
            print(f"   📊 Total calories: {updated_meal['total_calories']}")
            print(f"   📈 Per 100g: {updated_meal['calories_per_100g']} cal")
            print(f"   🥩 Total macros: P{updated_meal['total_macros']['protein']}g C{updated_meal['total_macros']['carbs']}g F{updated_meal['total_macros']['fat']}g")
            print(f"   🔄 Status: {updated_meal['status']} (LLM recalculation in progress)")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # 4. Track consumed macros from meal (full portion)
    print("\n4. Tracking consumed macros (full meal):")
    consume_data = {
        "meal_id": meal_id
    }
    try:
        response = requests.post(f"{BASE_URL}/macros/consumed", json=consume_data)
        if response.status_code == 200:
            macro_progress = response.json()
            print(f"   ✅ Tracked meal: {meal_id}")
            print(f"   📊 Daily progress: {macro_progress['consumed_calories']:.1f}/{macro_progress['target_calories']} cal")
            print(f"   🎯 Protein: {macro_progress['completion_percentage']['protein']:.1f}%")
            print(f"   🎯 Carbs: {macro_progress['completion_percentage']['carbs']:.1f}%")
            print(f"   🎯 Fat: {macro_progress['completion_percentage']['fat']:.1f}%")
            print(f"   💡 Recommendations: {len(macro_progress['recommendations'])} tips")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # 5. Track consumed macros from meal (partial portion - 150g)
    print("\n5. Tracking consumed macros (150g portion):")
    partial_consume_data = {
        "meal_id": meal_id,
        "weight_grams": 150.0
    }
    try:
        response = requests.post(f"{BASE_URL}/macros/consumed", json=partial_consume_data)
        if response.status_code == 200:
            macro_progress = response.json()
            print(f"   ✅ Tracked 150g of meal: {meal_id}")
            print(f"   📊 Daily progress: {macro_progress['consumed_calories']:.1f}/{macro_progress['target_calories']} cal")
            print(f"   🎯 Protein: {macro_progress['completion_percentage']['protein']:.1f}%")
            recommendations = macro_progress['recommendations']
            if recommendations:
                print(f"   💡 Latest tip: {recommendations[0]}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # 6. Track consumed macros from meal (percentage-based)
    print("\n6. Tracking consumed macros (75% of meal):")
    percentage_consume_data = {
        "meal_id": meal_id,
        "portion_percentage": 75.0
    }
    try:
        response = requests.post(f"{BASE_URL}/macros/consumed", json=percentage_consume_data)
        if response.status_code == 200:
            macro_progress = response.json()
            print(f"   ✅ Tracked 75% of meal: {meal_id}")
            print(f"   📊 Daily progress: {macro_progress['consumed_calories']:.1f}/{macro_progress['target_calories']} cal")
            print(f"   🎯 Goal met: {'Yes' if macro_progress['is_goal_met'] else 'No'}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    print("\n" + "=" * 70)
    print("✨ Key Improvements:")
    print("  • Gram-based measurements instead of vague 'servings'")
    print("  • Meal-based macro tracking with precise portions") 
    print("  • Per-100g nutritional information for consistency")
    print("  • Flexible portion tracking (weight or percentage)")
    print("  • Real-time macro progress with daily targets")
    print("=" * 70)

if __name__ == "__main__":
    test_meal_macros_api() 