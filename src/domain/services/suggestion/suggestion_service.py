"""
Consolidated suggestion service.
Merges daily_meal_suggestion_service.py and meal_suggestion_service.py.
"""
import logging
from datetime import datetime, date, time
from typing import List, Optional, Dict, Any

from src.domain.model.meal_planning import MealType
from src.domain.model.meal_suggestion import MealSuggestion
from src.domain.utils.timezone_utils import utc_now

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

    # Meal type time boundaries (from former MealCoreService)
    BREAKFAST_START = time(5, 0)
    BREAKFAST_END = time(10, 30)
    LUNCH_START = time(11, 0)
    LUNCH_END = time(14, 30)
    DINNER_START = time(17, 0)
    DINNER_END = time(21, 0)

    # Default calorie distributions by meal type (from former MealCoreService)
    DEFAULT_DISTRIBUTIONS = {
        MealType.BREAKFAST: 0.25,
        MealType.LUNCH: 0.35,
        MealType.DINNER: 0.30,
        MealType.SNACK: 0.10,
    }

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
        return self._determine_meal_type(current_time)

    def _determine_meal_type(
        self,
        current_time: Optional[datetime] = None,
    ) -> MealType:
        """
        Determine meal type based on time of day.

        Args:
            current_time: Datetime of the meal (defaults to now)

        Returns:
            Appropriate MealType enum
        """
        if current_time is None:
            current_time = utc_now()

        t = current_time.time()

        if self.BREAKFAST_START <= t <= self.BREAKFAST_END:
            return MealType.BREAKFAST
        elif self.LUNCH_START <= t <= self.LUNCH_END:
            return MealType.LUNCH
        elif self.DINNER_START <= t <= self.DINNER_END:
            return MealType.DINNER
        else:
            return MealType.SNACK

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
            from src.domain.utils.timezone_utils import user_today
            target_date = user_today()  # UTC fallback; caller should pass user-local date
        
        # Determine current meal type based on time
        current_type = self.get_recommended_meal_type()

        # Calculate remaining meals for the day
        remaining_meals = self._get_remaining_meals(current_type)

        # Distribute remaining calories
        distributions = {}
        remaining_calories = daily_calories

        for meal_type in remaining_meals:
            target = self._get_calorie_target_for_meal(
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

    def _get_calorie_target_for_meal(
        self,
        meal_type: MealType,
        daily_calories: int,
        custom_distribution: Optional[Dict[MealType, float]] = None,
    ) -> int:
        """
        Get calorie target for a specific meal type.

        Args:
            meal_type: Type of meal
            daily_calories: Total daily calorie target
            custom_distribution: Optional custom distribution percentages

        Returns:
            Calorie target for the meal
        """
        distribution = custom_distribution or self.DEFAULT_DISTRIBUTIONS
        percentage = distribution.get(meal_type, 0.25)
        return int(daily_calories * percentage)

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
