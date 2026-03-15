"""Demo meal data: Days 1-3 (Monday through Wednesday)."""
from typing import List
from scripts.seed_demo_meal_types import FoodItemData, MealData

# Day 1 (Monday) — On-target (~1,610 kcal)
DAY1_MEALS: List[MealData] = [
    MealData(
        dish_name="Oatmeal with Eggs",
        meal_type="breakfast",
        food_items=[
            FoodItemData("Rolled oats", 80, "g", protein=10.4, carbs=54.4, fat=5.6, fiber=8.0, sugar=1.0),
            FoodItemData("Whole eggs", 100, "g", protein=12.6, carbs=0.7, fat=10.6, fiber=0.0, sugar=0.7),
            FoodItemData("Skim milk", 120, "ml", protein=4.1, carbs=5.9, fat=0.2, fiber=0.0, sugar=5.9),
        ],
    ),
    MealData(
        dish_name="Chicken Breast with Rice and Broccoli",
        meal_type="lunch",
        food_items=[
            FoodItemData("Chicken breast", 150, "g", protein=46.5, carbs=0.0, fat=3.3, fiber=0.0, sugar=0.0),
            FoodItemData("Cooked white rice", 180, "g", protein=3.9, carbs=48.2, fat=0.4, fiber=0.5, sugar=0.1),
            FoodItemData("Steamed broccoli", 100, "g", protein=2.8, carbs=7.0, fat=0.4, fiber=2.6, sugar=1.7),
            FoodItemData("Olive oil", 10, "ml", protein=0.0, carbs=0.0, fat=10.0, fiber=0.0, sugar=0.0),
        ],
    ),
    MealData(
        dish_name="Grilled Salmon with Sweet Potato",
        meal_type="dinner",
        food_items=[
            FoodItemData("Salmon fillet", 150, "g", protein=34.0, carbs=0.0, fat=13.5, fiber=0.0, sugar=0.0),
            FoodItemData("Sweet potato", 150, "g", protein=2.0, carbs=29.0, fat=0.1, fiber=3.8, sugar=6.0),
            FoodItemData("Mixed salad greens", 80, "g", protein=1.4, carbs=2.4, fat=0.2, fiber=1.2, sugar=1.2),
            FoodItemData("Lemon juice", 15, "ml", protein=0.1, carbs=1.4, fat=0.1, fiber=0.1, sugar=0.5),
        ],
    ),
    MealData(
        dish_name="Greek Yogurt with Berries",
        meal_type="snack",
        food_items=[
            FoodItemData("Greek yogurt (0% fat)", 170, "g", protein=17.0, carbs=6.0, fat=0.7, fiber=0.0, sugar=5.0),
            FoodItemData("Mixed berries", 80, "g", protein=0.6, carbs=9.4, fat=0.4, fiber=2.0, sugar=6.4),
        ],
    ),
]

# Day 2 (Tuesday) — Slightly over target (~2,020 kcal), cheat day
DAY2_MEALS: List[MealData] = [
    MealData(
        dish_name="Avocado Toast with Eggs",
        meal_type="breakfast",
        food_items=[
            FoodItemData("Whole grain bread", 80, "g", protein=8.0, carbs=36.0, fat=2.8, fiber=4.0, sugar=3.0),
            FoodItemData("Avocado", 100, "g", protein=2.0, carbs=8.5, fat=14.7, fiber=6.7, sugar=0.7),
            FoodItemData("Poached eggs", 120, "g", protein=15.1, carbs=0.8, fat=12.7, fiber=0.0, sugar=0.8),
        ],
    ),
    MealData(
        dish_name="Chicken Caesar Salad",
        meal_type="lunch",
        food_items=[
            FoodItemData("Grilled chicken breast", 130, "g", protein=40.3, carbs=0.0, fat=2.9, fiber=0.0, sugar=0.0),
            FoodItemData("Romaine lettuce", 100, "g", protein=1.2, carbs=3.3, fat=0.3, fiber=2.1, sugar=1.2),
            FoodItemData("Caesar dressing", 30, "ml", protein=0.5, carbs=2.1, fat=8.5, fiber=0.0, sugar=1.0),
            FoodItemData("Parmesan cheese", 20, "g", protein=7.2, carbs=0.7, fat=5.9, fiber=0.0, sugar=0.2),
            FoodItemData("Croutons", 30, "g", protein=2.5, carbs=18.5, fat=3.2, fiber=0.8, sugar=1.2),
        ],
    ),
    MealData(
        dish_name="Beef Stir-Fry with Rice",
        meal_type="dinner",
        food_items=[
            FoodItemData("Lean beef strips", 180, "g", protein=49.0, carbs=0.0, fat=10.8, fiber=0.0, sugar=0.0),
            FoodItemData("Cooked white rice", 200, "g", protein=4.3, carbs=53.5, fat=0.4, fiber=0.6, sugar=0.1),
            FoodItemData("Mixed vegetables", 120, "g", protein=2.4, carbs=9.6, fat=0.2, fiber=3.0, sugar=4.0),
            FoodItemData("Sesame oil", 10, "ml", protein=0.0, carbs=0.0, fat=10.0, fiber=0.0, sugar=0.0),
            FoodItemData("Soy sauce", 15, "ml", protein=1.3, carbs=1.4, fat=0.1, fiber=0.1, sugar=0.5),
        ],
    ),
    MealData(
        dish_name="Protein Shake with Banana",
        meal_type="snack",
        food_items=[
            FoodItemData("Whey protein powder", 35, "g", protein=26.0, carbs=4.0, fat=1.5, fiber=0.0, sugar=3.0),
            FoodItemData("Banana", 120, "g", protein=1.3, carbs=27.2, fat=0.4, fiber=3.1, sugar=14.4),
            FoodItemData("Almond milk", 240, "ml", protein=1.0, carbs=4.0, fat=2.5, fiber=0.5, sugar=3.0),
        ],
    ),
]

# Day 3 (Wednesday) — On-target (~1,505 kcal)
DAY3_MEALS: List[MealData] = [
    MealData(
        dish_name="Scrambled Eggs on Whole Wheat Toast",
        meal_type="breakfast",
        food_items=[
            FoodItemData("Whole eggs", 120, "g", protein=15.1, carbs=0.8, fat=12.7, fiber=0.0, sugar=0.8),
            FoodItemData("Whole wheat bread", 60, "g", protein=6.0, carbs=27.0, fat=2.1, fiber=3.0, sugar=2.0),
            FoodItemData("Butter", 5, "g", protein=0.0, carbs=0.0, fat=4.2, fiber=0.0, sugar=0.0),
        ],
    ),
    MealData(
        dish_name="Tuna Salad Sandwich",
        meal_type="lunch",
        food_items=[
            FoodItemData("Canned tuna in water", 120, "g", protein=31.2, carbs=0.0, fat=1.2, fiber=0.0, sugar=0.0),
            FoodItemData("Whole wheat bread", 80, "g", protein=8.0, carbs=36.0, fat=2.8, fiber=4.0, sugar=3.0),
            FoodItemData("Light mayonnaise", 20, "g", protein=0.1, carbs=2.6, fat=4.9, fiber=0.0, sugar=1.5),
            FoodItemData("Celery", 30, "g", protein=0.2, carbs=1.1, fat=0.1, fiber=0.6, sugar=0.6),
            FoodItemData("Cherry tomatoes", 60, "g", protein=0.5, carbs=3.5, fat=0.2, fiber=0.7, sugar=2.4),
        ],
    ),
    MealData(
        dish_name="Grilled Chicken with Quinoa and Vegetables",
        meal_type="dinner",
        food_items=[
            FoodItemData("Chicken breast", 140, "g", protein=43.4, carbs=0.0, fat=3.1, fiber=0.0, sugar=0.0),
            FoodItemData("Cooked quinoa", 150, "g", protein=6.0, carbs=33.8, fat=2.6, fiber=2.9, sugar=1.5),
            FoodItemData("Zucchini", 100, "g", protein=1.2, carbs=3.1, fat=0.3, fiber=1.0, sugar=2.5),
            FoodItemData("Olive oil", 10, "ml", protein=0.0, carbs=0.0, fat=10.0, fiber=0.0, sugar=0.0),
        ],
    ),
    MealData(
        dish_name="Apple with Peanut Butter",
        meal_type="snack",
        food_items=[
            FoodItemData("Apple", 182, "g", protein=0.5, carbs=25.1, fat=0.3, fiber=4.4, sugar=18.9),
            FoodItemData("Natural peanut butter", 20, "g", protein=4.8, carbs=3.5, fat=10.0, fiber=1.2, sugar=1.0),
        ],
    ),
]
