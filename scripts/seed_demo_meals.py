"""
Demo meal data assembler.

Combines early-week (days 1-3) and late-week (days 4-6) meal data into
the ALL_DAYS_MEALS list consumed by the seed DB module.

Day index mapping: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat
"""
from typing import List

from scripts.seed_demo_meal_types import MealData
from scripts.seed_demo_meals_early import DAY1_MEALS, DAY2_MEALS, DAY3_MEALS
from scripts.seed_demo_meals_late import DAY4_MEALS, DAY5_MEALS, DAY6_MEALS

# Ordered list of all days — index 0 = Monday of current week
ALL_DAYS_MEALS: List[List[MealData]] = [
    DAY1_MEALS,
    DAY2_MEALS,
    DAY3_MEALS,
    DAY4_MEALS,
    DAY5_MEALS,
    DAY6_MEALS,
]

# Day indices that should be flagged as cheat days (0-based, 1 = Tuesday)
CHEAT_DAY_INDICES: List[int] = [1]
