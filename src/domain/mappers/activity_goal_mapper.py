"""
Centralized mapper for activity levels and fitness goals.
Ensures consistent mapping across the entire application.
"""
from typing import Dict

from src.domain.model.user import ActivityLevel, Goal


class ActivityGoalMapper:
    """Centralized mapper for activity levels and fitness goals."""
    
    # Activity level mappings - all variations map to canonical enum values
    ACTIVITY_LEVEL_MAP: Dict[str, ActivityLevel] = {
        # Canonical values
        "sedentary": ActivityLevel.SEDENTARY,
        "light": ActivityLevel.LIGHT,
        "moderate": ActivityLevel.MODERATE,
        "active": ActivityLevel.ACTIVE,
        "extra": ActivityLevel.EXTRA,
        
        # Alternative names (with underscore)
        "lightly_active": ActivityLevel.LIGHT,
        "moderately_active": ActivityLevel.MODERATE,
        "very_active": ActivityLevel.ACTIVE,
        "extra_active": ActivityLevel.EXTRA,
    }
    
    # Goal mappings - all variations map to canonical enum values
    GOAL_MAP: Dict[str, Goal] = {
        # Canonical values
        "maintenance": Goal.MAINTENANCE,
        "cutting": Goal.CUTTING,
        "bulking": Goal.BULKING,
        
        # Alternative names
        "maintain": Goal.MAINTENANCE,
        "maintain_weight": Goal.MAINTENANCE,
        "lose_weight": Goal.CUTTING,
        "weight_loss": Goal.CUTTING,
        "gain_weight": Goal.BULKING,
        "build_muscle": Goal.BULKING,
        "muscle_gain": Goal.BULKING,
    }
    
    @classmethod
    def map_activity_level(cls, activity_level: str) -> ActivityLevel:
        """Map activity level string to enum, with fallback to MODERATE."""
        return cls.ACTIVITY_LEVEL_MAP.get(
            activity_level.lower(), 
            ActivityLevel.MODERATE
        )
    
    @classmethod
    def map_goal(cls, goal: str) -> Goal:
        """Map goal string to enum, with fallback to MAINTENANCE."""
        return cls.GOAL_MAP.get(
            goal.lower(), 
            Goal.MAINTENANCE
        )