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
    weight_loss = "weight_loss"
    muscle_gain = "muscle_gain"
    maintenance = "maintenance"
    general_health = "general_health"


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


class ConversationStateEnum(str, enum.Enum):
    """Conversation state options for chat flow."""
    greeting = "greeting"
    asking_dietary_preferences = "asking_dietary_preferences"
    asking_allergies = "asking_allergies"
    asking_fitness_goals = "asking_fitness_goals"
    asking_meal_count = "asking_meal_count"
    asking_plan_duration = "asking_plan_duration"
    asking_cooking_time = "asking_cooking_time"
    asking_cuisine_preferences = "asking_cuisine_preferences"
    confirming_preferences = "confirming_preferences"
    generating_plan = "generating_plan"
    showing_plan = "showing_plan"
    adjusting_meal = "adjusting_meal"
    completed = "completed"


class ActivityLevelEnum(str, enum.Enum):
    """Activity level for TDEE calculations."""
    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    very_active = "very_active"
    extra_active = "extra_active"


class SexEnum(str, enum.Enum):
    """Biological sex for TDEE calculations."""
    male = "male"
    female = "female"


class GoalEnum(str, enum.Enum):
    """Fitness goal for macro calculations."""
    maintenance = "maintenance"
    cutting = "cutting"
    bulking = "bulking"