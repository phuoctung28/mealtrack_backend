"""
Consolidated suggestion service.
Merges daily_meal_suggestion_service.py and meal_suggestion_service.py.
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from src.domain.model.meal_planning import MealType
from src.domain.model.meal_suggestion import MealSuggestion
from src.domain.services.meal.meal_core_service import MealCoreService

logger = logging.getLogger(__name__)


class SuggestionService:
    """
    Unified suggestion service for meal recommendations.
    
    Consolidates:
    - daily_meal_suggestion_service.py
    - meal_suggestion_service.py
    
    Responsibilities:
    - Generate meal type recommendations based on time
    - Calculate portion sizes
    - Filter suggestions based on user preferences
    """

    def __init__(
        self,
        meal_core_service: Optional[MealCoreService] = None,
    ):
        """
        Initialize suggestion service.
        
        Args:
            meal_core_service: Optional meal core service for meal type determination
        """
        self._meal_service = meal_core_service or MealCoreService()

    def get_recommended_meal_type(
        self,
        current_time: Optional[datetime] = None,
    ) -> MealType:
        """
        Get recommended meal type based on current time.
        
        Args:
            current_time: Current datetime (defaults to now)
            
        Returns:
            Recommended MealType
        """
        return self._meal_service.determine_meal_type(current_time)

    def get_daily_suggestion_context(
        self,
        user_id: str,
        target_date: Optional[date] = None,
        daily_calories: int = 2000,
    ) -> Dict[str, Any]:
        """
        Get context for daily meal suggestions.
        
        Args:
            user_id: User ID
            target_date: Target date (defaults to today)
            daily_calories: Daily calorie target
            
        Returns:
            Context dictionary with meal distributions
        """
        if target_date is None:
            target_date = date.today()
        
        # Determine current meal type based on time
        current_type = self.get_recommended_meal_type()
        
        # Calculate remaining meals for the day
        remaining_meals = self._get_remaining_meals(current_type)
        
        # Distribute remaining calories
        distributions = {}
        remaining_calories = daily_calories
        
        for meal_type in remaining_meals:
            target = self._meal_service.get_calorie_target_for_meal(
                meal_type, daily_calories
            )
            distributions[meal_type] = min(target, remaining_calories)
            remaining_calories -= target
        
        return {
            "user_id": user_id,
            "date": target_date.isoformat(),
            "current_meal_type": current_type.value,
            "remaining_meals": [m.value for m in remaining_meals],
            "distributions": {k.value: v for k, v in distributions.items()},
            "daily_calories": daily_calories,
        }

    def _get_remaining_meals(self, current_type: MealType) -> List[MealType]:
        """Get remaining meal types for the day."""
        all_meals = [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER]
        
        if current_type == MealType.BREAKFAST:
            return all_meals
        elif current_type == MealType.LUNCH:
            return [MealType.LUNCH, MealType.DINNER]
        elif current_type == MealType.DINNER:
            return [MealType.DINNER]
        else:
            return [MealType.SNACK]

    def filter_suggestions_by_preferences(
        self,
        suggestions: List[MealSuggestion],
        dietary_preferences: Optional[List[str]] = None,
        allergies: Optional[List[str]] = None,
        max_prep_time: Optional[int] = None,
    ) -> List[MealSuggestion]:
        """
        Filter suggestions based on user preferences.
        
        Args:
            suggestions: List of suggestions to filter
            dietary_preferences: User dietary preferences
            allergies: User allergies
            max_prep_time: Maximum preparation time in minutes
            
        Returns:
            Filtered list of suggestions
        """
        filtered = suggestions
        
        # Filter by prep time
        if max_prep_time:
            filtered = [
                s for s in filtered 
                if s.prep_time_minutes <= max_prep_time
            ]
        
        # Filter by allergies
        if allergies:
            allergy_set = {a.lower() for a in allergies}
            filtered = [
                s for s in filtered
                if not self._contains_allergen(s, allergy_set)
            ]
        
        # Filter by dietary preferences (e.g., vegetarian)
        if dietary_preferences:
            pref_set = {p.lower() for p in dietary_preferences}
            if "vegetarian" in pref_set:
                filtered = [s for s in filtered if self._is_vegetarian_safe(s)]
            if "vegan" in pref_set:
                filtered = [s for s in filtered if self._is_vegan_safe(s)]
        
        return filtered

    def _contains_allergen(
        self,
        suggestion: MealSuggestion,
        allergens: set,
    ) -> bool:
        """Check if suggestion contains any allergens."""
        for ingredient in suggestion.ingredients:
            if ingredient.name.lower() in allergens:
                return True
            # Check for common allergen keywords
            for allergen in allergens:
                if allergen in ingredient.name.lower():
                    return True
        return False

    def _is_vegetarian_safe(self, suggestion: MealSuggestion) -> bool:
        """Check if suggestion is vegetarian-safe."""
        meat_keywords = [
            "chicken", "beef", "pork", "lamb", "turkey", "fish",
            "salmon", "tuna", "shrimp", "bacon", "ham", "sausage"
        ]
        for ingredient in suggestion.ingredients:
            name_lower = ingredient.name.lower()
            if any(meat in name_lower for meat in meat_keywords):
                return False
        return True

    def _is_vegan_safe(self, suggestion: MealSuggestion) -> bool:
        """Check if suggestion is vegan-safe."""
        if not self._is_vegetarian_safe(suggestion):
            return False
        
        animal_keywords = [
            "egg", "milk", "cheese", "yogurt", "butter", "cream",
            "honey", "whey", "casein"
        ]
        for ingredient in suggestion.ingredients:
            name_lower = ingredient.name.lower()
            if any(animal in name_lower for animal in animal_keywords):
                return False
        return True

    def calculate_suggestion_score(
        self,
        suggestion: MealSuggestion,
        target_calories: int,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate a relevance score for a suggestion.
        
        Args:
            suggestion: The meal suggestion
            target_calories: Target calorie count
            preferences: Optional user preferences
            
        Returns:
            Score from 0.0 to 1.0
        """
        score = suggestion.confidence_score or 0.5
        
        # Adjust for calorie match
        if target_calories > 0:
            calorie_diff = abs(suggestion.macros.calories - target_calories)
            calorie_score = max(0, 1 - (calorie_diff / target_calories))
            score = (score + calorie_score) / 2
        
        # Adjust for prep time preference
        if preferences and "max_prep_time" in preferences:
            max_time = preferences["max_prep_time"]
            if suggestion.prep_time_minutes <= max_time:
                score += 0.1
            else:
                score -= 0.2
        
        return max(0.0, min(1.0, score))
