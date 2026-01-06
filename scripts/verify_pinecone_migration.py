"""
Verification script for Pinecone Inference API migration.
Tests recipe search functionality after migration.

Usage:
    python scripts/verify_pinecone_migration.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.domain.services.meal_suggestion.recipe_search_service import (
    RecipeSearchService,
    RecipeSearchCriteria
)

def main():
    """Verify recipe search functionality after migration."""
    print("=" * 60)
    print("Pinecone Migration Verification")
    print("=" * 60)
    print()

    try:
        # Initialize service
        print("Initializing RecipeSearchService...")
        service = RecipeSearchService()
        print("✅ Service initialized successfully")
        print()

        # Test 1: Search for dinner recipes
        print("Test 1: Search for dinner recipes (500±150 cal)")
        print("-" * 60)
        criteria = RecipeSearchCriteria(
            meal_type="dinner",
            target_calories=500,
            calorie_tolerance=150
        )
        results = service.search_recipes(criteria, top_k=5)

        if results:
            print(f"✅ Found {len(results)} recipes:")
            for i, recipe in enumerate(results, 1):
                print(f"  {i}. {recipe.name}")
                print(f"     Calories: {recipe.macros['calories']}")
                print(f"     Protein: {recipe.macros['protein']}g")
                print(f"     Confidence: {recipe.confidence_score:.2f}")
                print()
        else:
            print("❌ No recipes found")
            return False

        # Test 2: Search for breakfast recipes
        print()
        print("Test 2: Search for breakfast recipes (300±100 cal)")
        print("-" * 60)
        criteria = RecipeSearchCriteria(
            meal_type="breakfast",
            target_calories=300,
            calorie_tolerance=100
        )
        results = service.search_recipes(criteria, top_k=3)

        if results:
            print(f"✅ Found {len(results)} recipes:")
            for i, recipe in enumerate(results, 1):
                print(f"  {i}. {recipe.name}")
                print(f"     Calories: {recipe.macros['calories']}")
                print(f"     Confidence: {recipe.confidence_score:.2f}")
                print()
        else:
            print("❌ No recipes found")
            return False

        # Test 3: Search with ingredient preference
        print()
        print("Test 3: Search with ingredient preference (chicken)")
        print("-" * 60)
        criteria = RecipeSearchCriteria(
            meal_type="dinner",
            target_calories=600,
            calorie_tolerance=200,
            ingredients=["chicken"]
        )
        results = service.search_recipes(criteria, top_k=3)

        if results:
            print(f"✅ Found {len(results)} recipes:")
            for i, recipe in enumerate(results, 1):
                print(f"  {i}. {recipe.name}")
                print(f"     Calories: {recipe.macros['calories']}")
                print(f"     Confidence: {recipe.confidence_score:.2f}")
                print()
        else:
            print("❌ No recipes found")
            return False

        # Success
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("Migration verification complete!")
        print("Recipe search is working with Pinecone Inference API.")
        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
