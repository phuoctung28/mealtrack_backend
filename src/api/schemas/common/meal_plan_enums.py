from enum import Enum


class DietaryPreferenceSchema(str, Enum):
    vegan = "vegan"
    vegetarian = "vegetarian"
    pescatarian = "pescatarian"
    gluten_free = "gluten_free"
    keto = "keto"
    paleo = "paleo"
    low_carb = "low_carb"
    dairy_free = "dairy_free"
    none = "none"


class FitnessGoalSchema(str, Enum):
    weight_loss = "weight_loss"
    muscle_gain = "muscle_gain"
    maintenance = "maintenance"
    general_health = "general_health"


class MealTypeSchema(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class PlanDurationSchema(str, Enum):
    daily = "daily"
    weekly = "weekly"


class ConversationStateSchema(str, Enum):
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