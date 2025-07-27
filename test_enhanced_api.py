#!/usr/bin/env python3
"""
Test script for the enhanced nutrition tracking API endpoints.
"""
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)

from src.api.schemas.response.daily_nutrition_response import DailyNutritionResponse, MacrosResponse

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
    )
    
    assert response.target_calories == 2000.0
    assert response.consumed_calories == 1500.0
    assert response.remaining_calories == 500.0
    assert response.completion_percentage["calories"] == 75.0
    print("✓ Enhanced DailyNutritionResponse works")

def main():
    """Run all tests."""
    print("🧪 Testing Enhanced Nutrition Tracking API Schemas\n")
    
    try:
        test_macros_response()
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