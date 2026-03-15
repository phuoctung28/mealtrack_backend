"""Demo meal data: Days 4-6 (Thursday through Saturday)."""
from typing import List
from scripts.seed_demo_meal_types import FoodItemData, MealData

# Day 4 (Thursday) — Slightly under (~1,240 kcal)
DAY4_MEALS: List[MealData] = [
    MealData(
        dish_name="Greek Yogurt Parfait",
        meal_type="breakfast",
        food_items=[
            FoodItemData("Greek yogurt (2% fat)", 200, "g", protein=18.0, carbs=8.0, fat=4.0, fiber=0.0, sugar=7.0),
            FoodItemData("Granola", 30, "g", protein=3.0, carbs=20.0, fat=4.0, fiber=1.5, sugar=6.0),
            FoodItemData("Honey", 10, "g", protein=0.0, carbs=8.2, fat=0.0, fiber=0.0, sugar=8.0),
            FoodItemData("Blueberries", 60, "g", protein=0.4, carbs=8.6, fat=0.2, fiber=1.4, sugar=6.0),
        ],
    ),
    MealData(
        dish_name="Turkey Wrap with Side Salad",
        meal_type="lunch",
        food_items=[
            FoodItemData("Turkey breast slices", 100, "g", protein=22.0, carbs=0.5, fat=1.0, fiber=0.0, sugar=0.5),
            FoodItemData("Whole wheat tortilla", 45, "g", protein=4.2, carbs=21.0, fat=2.5, fiber=2.5, sugar=1.0),
            FoodItemData("Mixed greens", 60, "g", protein=1.0, carbs=1.8, fat=0.2, fiber=0.9, sugar=0.9),
            FoodItemData("Hummus", 30, "g", protein=2.4, carbs=5.1, fat=3.9, fiber=1.5, sugar=0.3),
            FoodItemData("Cherry tomatoes", 50, "g", protein=0.4, carbs=2.9, fat=0.2, fiber=0.6, sugar=2.0),
        ],
    ),
    MealData(
        dish_name="Baked Cod with Brown Rice and Asparagus",
        meal_type="dinner",
        food_items=[
            FoodItemData("Cod fillet", 150, "g", protein=32.6, carbs=0.0, fat=1.2, fiber=0.0, sugar=0.0),
            FoodItemData("Cooked brown rice", 160, "g", protein=3.4, carbs=35.2, fat=1.0, fiber=1.8, sugar=0.3),
            FoodItemData("Asparagus", 100, "g", protein=2.2, carbs=3.9, fat=0.1, fiber=2.1, sugar=1.9),
            FoodItemData("Olive oil", 8, "ml", protein=0.0, carbs=0.0, fat=8.0, fiber=0.0, sugar=0.0),
        ],
    ),
    MealData(
        dish_name="Mixed Nuts",
        meal_type="snack",
        food_items=[
            FoodItemData("Mixed nuts (almonds, walnuts, cashews)", 30, "g", protein=5.1, carbs=5.7, fat=15.6, fiber=1.9, sugar=1.2),
        ],
    ),
]

# Day 5 (Friday) — On-target (~1,710 kcal)
DAY5_MEALS: List[MealData] = [
    MealData(
        dish_name="Protein Pancakes",
        meal_type="breakfast",
        food_items=[
            FoodItemData("Whey protein powder", 30, "g", protein=22.3, carbs=3.4, fat=1.3, fiber=0.0, sugar=2.6),
            FoodItemData("Banana", 100, "g", protein=1.1, carbs=22.7, fat=0.3, fiber=2.6, sugar=12.0),
            FoodItemData("Whole eggs", 100, "g", protein=12.6, carbs=0.7, fat=10.6, fiber=0.0, sugar=0.7),
            FoodItemData("Rolled oats", 40, "g", protein=5.2, carbs=27.2, fat=2.8, fiber=4.0, sugar=0.5),
            FoodItemData("Maple syrup", 15, "ml", protein=0.0, carbs=12.9, fat=0.0, fiber=0.0, sugar=12.1),
        ],
    ),
    MealData(
        dish_name="Chicken Fried Rice",
        meal_type="lunch",
        food_items=[
            FoodItemData("Cooked jasmine rice", 200, "g", protein=4.4, carbs=51.8, fat=0.5, fiber=0.6, sugar=0.0),
            FoodItemData("Chicken breast", 120, "g", protein=37.2, carbs=0.0, fat=2.6, fiber=0.0, sugar=0.0),
            FoodItemData("Whole eggs", 60, "g", protein=7.6, carbs=0.4, fat=6.4, fiber=0.0, sugar=0.4),
            FoodItemData("Mixed vegetables", 80, "g", protein=1.6, carbs=6.4, fat=0.2, fiber=2.0, sugar=2.8),
            FoodItemData("Soy sauce", 15, "ml", protein=1.3, carbs=1.4, fat=0.1, fiber=0.1, sugar=0.5),
            FoodItemData("Sesame oil", 5, "ml", protein=0.0, carbs=0.0, fat=5.0, fiber=0.0, sugar=0.0),
        ],
    ),
    MealData(
        dish_name="Shrimp Tacos with Guacamole",
        meal_type="dinner",
        food_items=[
            FoodItemData("Shrimp", 150, "g", protein=28.5, carbs=1.3, fat=1.7, fiber=0.0, sugar=0.0),
            FoodItemData("Corn tortillas", 60, "g", protein=3.6, carbs=25.2, fat=1.8, fiber=2.8, sugar=0.5),
            FoodItemData("Guacamole", 60, "g", protein=1.0, carbs=5.5, fat=8.5, fiber=3.5, sugar=0.4),
            FoodItemData("Shredded cabbage", 50, "g", protein=0.6, carbs=2.9, fat=0.1, fiber=1.3, sugar=1.6),
            FoodItemData("Lime juice", 10, "ml", protein=0.1, carbs=0.9, fat=0.0, fiber=0.0, sugar=0.4),
            FoodItemData("Salsa", 40, "g", protein=0.5, carbs=3.2, fat=0.2, fiber=0.8, sugar=2.1),
        ],
    ),
    MealData(
        dish_name="Cottage Cheese with Pineapple",
        meal_type="snack",
        food_items=[
            FoodItemData("Cottage cheese (low fat)", 150, "g", protein=17.6, carbs=4.1, fat=2.6, fiber=0.0, sugar=4.1),
            FoodItemData("Pineapple chunks", 80, "g", protein=0.4, carbs=10.8, fat=0.1, fiber=0.8, sugar=9.5),
        ],
    ),
]

# Day 6 (Saturday) — Partial day, only breakfast + lunch logged
DAY6_MEALS: List[MealData] = [
    MealData(
        dish_name="Veggie Omelette",
        meal_type="breakfast",
        food_items=[
            FoodItemData("Whole eggs", 150, "g", protein=18.9, carbs=1.1, fat=15.9, fiber=0.0, sugar=1.1),
            FoodItemData("Spinach", 50, "g", protein=1.8, carbs=1.8, fat=0.2, fiber=1.1, sugar=0.4),
            FoodItemData("Bell pepper", 60, "g", protein=0.6, carbs=5.6, fat=0.1, fiber=1.6, sugar=3.9),
            FoodItemData("Feta cheese", 25, "g", protein=3.9, carbs=0.9, fat=5.5, fiber=0.0, sugar=0.7),
            FoodItemData("Olive oil", 5, "ml", protein=0.0, carbs=0.0, fat=5.0, fiber=0.0, sugar=0.0),
        ],
    ),
    MealData(
        dish_name="Grilled Salmon Salad",
        meal_type="lunch",
        source="scanner",
        food_items=[
            FoodItemData("Salmon fillet", 130, "g", protein=29.5, carbs=0.0, fat=11.7, fiber=0.0, sugar=0.0),
            FoodItemData("Mixed greens", 100, "g", protein=1.7, carbs=3.0, fat=0.2, fiber=1.5, sugar=1.5),
            FoodItemData("Cherry tomatoes", 80, "g", protein=0.7, carbs=4.6, fat=0.2, fiber=0.9, sugar=3.2),
            FoodItemData("Cucumber", 60, "g", protein=0.4, carbs=1.9, fat=0.1, fiber=0.4, sugar=1.2),
            FoodItemData("Olive oil dressing", 15, "ml", protein=0.0, carbs=0.5, fat=13.5, fiber=0.0, sugar=0.2),
        ],
    ),
]
