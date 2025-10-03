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
    BULKING_SURPLUS = 500      # 500 calorie surplus
    MAINTENANCE_ADJUSTMENT = 0
    
    # Macro percentages - Moderate Carb (30/35/35) from tdeecalculator.net
    PROTEIN_PERCENT = 0.30    # 30% of calories from protein
    FAT_PERCENT = 0.35        # 35% of calories from fat  
    CARBS_PERCENT = 0.35      # 35% of calories from carbs
    
    # Validation ranges
    MIN_AGE = 13
    MAX_AGE = 120
    MIN_WEIGHT_KG = 30
    MAX_WEIGHT_KG = 300
    MIN_HEIGHT_CM = 100
    MAX_HEIGHT_CM = 250
    MIN_BODY_FAT_PCT = 3
    MAX_BODY_FAT_PCT = 60

