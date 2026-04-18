"""
Common enums shared across domain models.
"""
from enum import Enum


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class JobType(str, Enum):
    DESK = "desk"
    ON_FEET = "on_feet"
    PHYSICAL = "physical"


class FitnessGoal(str, Enum):
    CUT = "cut"
    BULK = "bulk"
    RECOMP = "recomp"


class TrainingLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
