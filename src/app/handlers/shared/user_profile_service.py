"""
Shared user profile service for meal plan handlers.
Follows clean architecture principles.
"""
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.domain.model.meal_plan import UserPreferences, DietaryPreference, FitnessGoal, PlanDuration
from src.infra.database.models.user import UserProfile

logger = logging.getLogger(__name__)


class UserProfileService:
    """Shared service for user profile operations in meal planning."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_profile_or_defaults(self, user_id: str) -> Dict[str, Any]:
        """Get user profile data or provide sensible defaults."""
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id,
            UserProfile.is_current == True
        ).first()
        
        if profile:
            # Import here to avoid circular dependency
            from src.app.handlers.command_handlers.user_command_handlers import SaveUserOnboardingCommandHandler
            onboarding_handler = SaveUserOnboardingCommandHandler(self.db)
            tdee_result = onboarding_handler._calculate_tdee_and_macros(profile)
            
            return {
                'dietary_preferences': profile.dietary_preferences or [],
                'allergies': profile.allergies or [],
                'target_calories': tdee_result['target_calories'],
                'target_protein': tdee_result['macros']['protein'],
                'target_carbs': tdee_result['macros']['carbs'],
                'target_fat': tdee_result['macros']['fat'],
                'meals_per_day': profile.meals_per_day,
                'include_snacks': profile.snacks_per_day > 0,
                'age': profile.age,
                'gender': profile.gender,
                'activity_level': profile.activity_level,
                'fitness_goal': profile.fitness_goal,
                'health_conditions': profile.health_conditions or []
            }
        else:
            # Default values when no profile exists
            return {
                'dietary_preferences': [],
                'allergies': [],
                'target_calories': 2000,
                'target_protein': 150,
                'target_carbs': 250,
                'target_fat': 70,
                'meals_per_day': 3,
                'include_snacks': True,
                'age': 30,
                'gender': 'male',
                'activity_level': 'moderate',
                'fitness_goal': 'maintenance',
                'health_conditions': []
            }
    
    def create_user_preferences_from_data(self, data: Dict[str, Any], plan_duration: PlanDuration = PlanDuration.DAILY) -> UserPreferences:
        """Create UserPreferences domain object from profile data."""
        # Convert string dietary preferences to domain enums
        valid_prefs = []
        for pref in data.get('dietary_preferences', []):
            try:
                valid_prefs.append(DietaryPreference(pref))
            except ValueError:
                logger.warning(f"Unknown dietary preference: {pref} – skipped")
        
        return UserPreferences(
            dietary_preferences=valid_prefs,
            allergies=data.get('allergies', []),
            fitness_goal=FitnessGoal(data.get('fitness_goal', 'maintenance')),
            meals_per_day=data.get('meals_per_day', 3),
            snacks_per_day=1 if data.get('include_snacks', False) else 0,
            cooking_time_weekday=30,  # Default
            cooking_time_weekend=45,  # Default
            favorite_cuisines=data.get('favorite_cuisines', []),
            disliked_ingredients=data.get('disliked_ingredients', []),
            plan_duration=plan_duration
        )