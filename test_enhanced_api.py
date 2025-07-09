#!/usr/bin/env python3
"""
Test script for the enhanced nutrition tracking API endpoints.
"""
import sys
import os
sys.path.append('/Users/tonytran/Projects/mealtrack_backend')
os.chdir('/Users/tonytran/Projects/mealtrack_backend')

from src.api.schemas.request.macro_requests import ConsumedMacrosRequest, MacrosCalculationRequest
from src.api.schemas.response.macro_responses import UpdatedMacrosResponse, MacrosCalculationResponse, MealMacrosResponse
from src.api.schemas.response.daily_nutrition_response import DailyNutritionResponse, MacrosResponse

def test_consumed_macros_request():
    """Test ConsumedMacrosRequest schema."""
    print("Testing ConsumedMacrosRequest...")
    
    # Test with weight_grams
    request1 = ConsumedMacrosRequest(
        meal_id="meal_123",
        weight_grams=150.0
    )
    assert request1.meal_id == "meal_123"
    assert request1.weight_grams == 150.0
    assert request1.portion_percentage is None
    print("✓ ConsumedMacrosRequest with weight_grams works")
    
    # Test with portion_percentage
    request2 = ConsumedMacrosRequest(
        meal_id="meal_456",
        portion_percentage=80.0
    )
    assert request2.meal_id == "meal_456"
    assert request2.portion_percentage == 80.0
    assert request2.weight_grams is None
    print("✓ ConsumedMacrosRequest with portion_percentage works")

def test_macros_calculation_request():
    """Test MacrosCalculationRequest schema."""
    print("\nTesting MacrosCalculationRequest...")
    
    request = MacrosCalculationRequest(
        age=30,
        gender="male",
        height=175.0,
        weight=75.0,
        activity_level="moderate",
        goal="cutting",
        goal_weight=70.0,
        dietary_preferences=["vegetarian"],
        health_conditions=[],
        timeline_months=6
    )
    assert request.age == 30
    assert request.gender == "male"
    assert request.goal == "cutting"
    assert request.goal_weight == 70.0
    print("✓ MacrosCalculationRequest works")

def test_macros_response():
    """Test MacrosResponse schema."""
    print("\nTesting MacrosResponse...")
    
    macros = MacrosResponse(
        protein=150.0,
        carbs=250.0,
        fat=67.0,
        fiber=25.0
    )
    assert macros.protein == 150.0
    assert macros.carbs == 250.0
    assert macros.fat == 67.0
    assert macros.fiber == 25.0
    print("✓ MacrosResponse works")

def test_updated_macros_response():
    """Test UpdatedMacrosResponse schema."""
    print("\nTesting UpdatedMacrosResponse...")
    
    target_macros = MacrosResponse(protein=150.0, carbs=250.0, fat=67.0, fiber=25.0)
    consumed_macros = MacrosResponse(protein=120.0, carbs=180.0, fat=45.0, fiber=18.0)
    remaining_macros = MacrosResponse(protein=30.0, carbs=70.0, fat=22.0, fiber=7.0)
    
    response = UpdatedMacrosResponse(
        user_macros_id="user_macros_123",
        target_date="2024-01-15",
        target_calories=2000.0,
        target_macros=target_macros,
        consumed_calories=1500.0,
        consumed_macros=consumed_macros,
        remaining_calories=500.0,
        remaining_macros=remaining_macros,
        completion_percentage={"calories": 75.0, "protein": 80.0, "carbs": 72.0, "fat": 67.0},
        is_goal_met=False,
        recommendations=["Great job tracking your meal!"]
    )
    
    assert response.target_calories == 2000.0
    assert response.consumed_calories == 1500.0
    assert response.remaining_calories == 500.0
    assert response.is_goal_met == False
    print("✓ UpdatedMacrosResponse works")

def test_daily_nutrition_response():
    """Test enhanced DailyNutritionResponse."""
    print("\nTesting enhanced DailyNutritionResponse...")
    
    target_macros = MacrosResponse(protein=150.0, carbs=250.0, fat=67.0, fiber=25.0)
    consumed_macros = MacrosResponse(protein=120.0, carbs=180.0, fat=45.0, fiber=18.0)
    remaining_macros = MacrosResponse(protein=30.0, carbs=70.0, fat=22.0, fiber=7.0)
    
    response = DailyNutritionResponse(
        date="2024-01-15",
        target_calories=2000.0,
        target_macros=target_macros,
        consumed_calories=1500.0,
        consumed_macros=consumed_macros,
        remaining_calories=500.0,
        remaining_macros=remaining_macros,
        completion_percentage={"calories": 75.0, "protein": 80.0, "carbs": 72.0, "fat": 67.0},
        total_meals=3,
        totals={"calories": 1500.0, "protein": 120.0, "carbs": 180.0, "fat": 45.0}
    )
    
    assert response.target_calories == 2000.0
    assert response.consumed_calories == 1500.0
    assert response.remaining_calories == 500.0
    assert response.completion_percentage["calories"] == 75.0
    assert response.total_meals == 3  # Legacy field
    print("✓ Enhanced DailyNutritionResponse works")

def main():
    """Run all tests."""
    print("🧪 Testing Enhanced Nutrition Tracking API Schemas\n")
    
    try:
        test_consumed_macros_request()
        test_macros_calculation_request()
        test_macros_response()
        test_updated_macros_response()
        test_daily_nutrition_response()
        
        print("\n✅ All tests passed! The enhanced API schemas are working correctly.")
        print("\n📊 Enhanced endpoints available:")
        print("  • POST /v1/meals/macros/consumed - Track meal consumption")
        print("  • POST /v1/meals/macros/calculate - Calculate macros from onboarding")
        print("  • GET /v1/meals/macros/meal/{meal_id} - Get meal macros with portions")
        print("  • GET /v1/meals/daily/macros - Enhanced daily macro tracking")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()