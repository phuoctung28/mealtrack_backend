"""
Centralized enum definitions for database models.
"""
import enum


class MealStatusEnum(enum.Enum):
    """Enum for meal status in database."""
    PROCESSING = "PROCESSING"
    ANALYZING = "ANALYZING"
    ENRICHING = "ENRICHING"
    READY = "READY"
    FAILED = "FAILED"
    INACTIVE = "INACTIVE"


class DietaryPreferenceEnum(str, enum.Enum):
    """Dietary preference options."""
    vegan = "vegan"
    vegetarian = "vegetarian"
    pescatarian = "pescatarian"
    gluten_free = "gluten_free"
    keto = "keto"
    paleo = "paleo"
    low_carb = "low_carb"
    dairy_free = "dairy_free"
    none = "none"


class FitnessGoalEnum(str, enum.Enum):
    """Fitness goal options."""
    cut = "cut"
    bulk = "bulk"
    recomp = "recomp"


class MealTypeEnum(str, enum.Enum):
    """Meal type options."""
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class PlanDurationEnum(str, enum.Enum):
    """Meal plan duration options."""
    daily = "daily"
    weekly = "weekly"


class JobTypeEnum(str, enum.Enum):
    """Job type for TDEE calculations based on daily movement."""
    desk = "desk"
    on_feet = "on_feet"
    physical = "physical"


class SexEnum(str, enum.Enum):
    """Biological sex for TDEE calculations."""
    male = "male"
    female = "female"


class GoalEnum(str, enum.Enum):
    """Fitness goal for macro calculations."""
    cut = "cut"
    bulk = "bulk"
    recomp = "recomp"