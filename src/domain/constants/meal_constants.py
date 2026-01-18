"""
Constants for meal-related domain operations.

This module centralizes all meal-related constants, magic numbers,
and configuration values used throughout the domain layer.
"""


class MealDistribution:
    """Constants for meal calorie distribution."""
    
    # Standard distribution percentages
    BREAKFAST_PERCENT = 0.25
    LUNCH_PERCENT = 0.35
    DINNER_PERCENT = 0.30
    SNACK_PERCENT = 0.10
    
    # Calorie thresholds
    MIN_CALORIES_FOR_SNACK = 1800
    
    # With snack adjustments
    BREAKFAST_WITH_SNACK = 0.225  # 25% * 0.9
    LUNCH_WITH_SNACK = 0.315      # 35% * 0.9
    DINNER_WITH_SNACK = 0.27      # 30% * 0.9


class NutritionConstants:
    """Constants for nutrition calculations."""
    
    # Calorie per gram of macronutrients
    CALORIES_PER_GRAM_PROTEIN = 4
    CALORIES_PER_GRAM_CARBS = 4
    CALORIES_PER_GRAM_FAT = 9
    
    # Validation tolerances
    CALORIE_TOLERANCE_PERCENT = 0.20  # 20% tolerance for calorie validation
    TOTAL_CALORIE_TOLERANCE_PERCENT = 0.05  # 5% tolerance for total calories
    
    # Default confidence scores
    DEFAULT_FOOD_CONFIDENCE = 1.0
    MIN_CONFIDENCE_THRESHOLD = 0.5


class PortionUnits:
    """Valid units for portion sizes."""
    
    WEIGHT_UNITS = ["g", "oz", "kg", "lb"]
    VOLUME_UNITS = ["ml", "l", "cup", "tbsp", "tsp", "fl oz"]
    COUNT_UNITS = ["piece", "serving", "slice", "unit"]
    
    ALL_UNITS = WEIGHT_UNITS + VOLUME_UNITS + COUNT_UNITS
    
    # Conversion factors to grams (approximate)
    TO_GRAMS = {
        "g": 1,
        "oz": 28.35,
        "kg": 1000,
        "lb": 453.59,
        "cup": 240,  # Approximate, varies by ingredient
        "tbsp": 15,  # Approximate
        "tsp": 5,    # Approximate
    }


class GPTPromptConstants:
    """Constants for GPT prompts."""
    
    # Response format version
    RESPONSE_FORMAT_VERSION = "1.0"
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.8
    MEDIUM_CONFIDENCE = 0.6
    LOW_CONFIDENCE = 0.4
    
    # Token limits
    MAX_OUTPUT_TOKENS = 2000
    MAX_PROMPT_LENGTH = 4000


class MealPlanningConstants:
    """Constants for meal planning."""
    
    # Cooking time defaults (minutes)
    DEFAULT_WEEKDAY_COOKING_TIME = 30
    DEFAULT_WEEKEND_COOKING_TIME = 60
    MAX_SNACK_PREP_TIME = 15
    
    # Meal variety
    MIN_DAYS_BEFORE_REPEAT = 3
    MAX_CUISINE_REPEATS_PER_WEEK = 2
    
    # Plan duration
    WEEKLY_PLAN_DAYS = 7
    DAILY_PLAN_DAYS = 1


class TDEEConstants:
    """Constants for TDEE calculations."""
    
    # Activity level multipliers
    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "extra": 1.9
    }
    
    # Goal adjustments (calories)
    CUTTING_DEFICIT = 500      # 500 calorie deficit
    BULKING_SURPLUS = 300      # 300 calorie surplus (lean bulk)
    # MAINTENANCE_ADJUSTMENT removed - use RECOMP_ADJUSTMENT instead
    RECOMP_ADJUSTMENT = 0      # No calorie adjustment for recomposition

    # Weight-based macro multipliers (g per kg body weight)
    # Research: 1.6-2.0 g/kg protein optimal for muscle synthesis
    # Higher protein during cut to preserve muscle in deficit
    PROTEIN_PER_KG = {
        "cut": 2.0,    # Higher protein to preserve muscle during deficit
        "recomp": 1.8, # Moderate protein for body recomposition
        "bulk": 1.6    # Lower protein as calorie surplus provides anabolic signal
    }

    # Fat intake: 0.7-1.2 g/kg for hormone production
    # Lower fat during cut to maximize protein and carbs in reduced calories
    FAT_PER_KG = {
        "cut": 0.8,    # Lower fat to preserve calories for protein
        "recomp": 0.9, # Moderate fat for balanced approach
        "bulk": 1.0    # Higher fat for hormone optimization during surplus
    }

    # Min/max bounds for safety
    MIN_PROTEIN_G = 60   # Minimum daily protein
    MAX_PROTEIN_G = 300  # Maximum daily protein
    MIN_FAT_G = 40       # Minimum daily fat for hormone function
    MAX_FAT_G = 150      # Maximum daily fat
    MIN_CARBS_G = 50     # Minimum daily carbs

    # Validation ranges
    MIN_AGE = 13
    MAX_AGE = 120
    MIN_WEIGHT_KG = 30
    MAX_WEIGHT_KG = 300
    MIN_HEIGHT_CM = 100
    MAX_HEIGHT_CM = 250
    MIN_BODY_FAT_PCT = 3
    MAX_BODY_FAT_PCT = 60


class ConversationConstants:
    """Constants for conversation flow."""
    
    # Message limits
    MAX_MESSAGE_LENGTH = 1000
    MAX_CONVERSATION_MESSAGES = 100
    
    # Timeout settings
    CONVERSATION_TIMEOUT_MINUTES = 30
    
    # Retry limits
    MAX_GENERATION_RETRIES = 3
    
    # Common responses
    ERROR_RESPONSE = "I'm sorry, something went wrong. Let's try again."
    TIMEOUT_RESPONSE = "This conversation has timed out. Please start a new one."