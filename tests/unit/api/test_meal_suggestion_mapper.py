"""
Unit tests for meal suggestion mappers.
"""
from datetime import datetime, timedelta

from src.api.mappers.meal_suggestion_mapper import (
    to_meal_suggestion_response,
    to_suggestions_list_response,
)
from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession, MacroEstimate, Ingredient, RecipeStep


class TestMealSuggestionMapper:
    """Test meal suggestion mapper functions."""

    def test_to_meal_suggestion_response(self):
        """Test converting MealSuggestion to API response."""
        from src.domain.model.meal_suggestion import MealType
        
        suggestion = MealSuggestion(
            id="suggestion-123",
            session_id="session-456",
            user_id="user-789",
            meal_name="Grilled Chicken",
            description="Healthy grilled chicken",
            meal_type=MealType.DINNER,
            macros=MacroEstimate(calories=500, protein=50, carbs=20, fat=15),
            ingredients=[
                Ingredient(name="Chicken Breast", amount=200, unit="g"),
                Ingredient(name="Olive Oil", amount=10, unit="ml")
            ],
            recipe_steps=[
                RecipeStep(step=1, instruction="Season chicken", duration_minutes=5),
                RecipeStep(step=2, instruction="Grill for 10 minutes", duration_minutes=10)
            ],
            prep_time_minutes=15,
            confidence_score=0.95
        )
        
        result = to_meal_suggestion_response(suggestion)
        
        assert result.id == "suggestion-123"
        assert result.meal_name == "Grilled Chicken"
        assert result.description == "Healthy grilled chicken"
        assert result.macros.calories == 500
        assert result.macros.protein == 50
        assert len(result.ingredients) == 2
        assert result.ingredients[0].name == "Chicken Breast"
        assert len(result.recipe_steps) == 2
        assert result.recipe_steps[0].step == 1
        assert result.prep_time_minutes == 15
        assert result.confidence_score == 0.95

    def test_to_suggestions_list_response(self):
        """Test converting session and suggestions to list response."""
        session = SuggestionSession(
            id="session-123",
            user_id="user-123",
            meal_type="main",
            meal_portion_type="regular",
            target_calories=600,
            ingredients=[],
            cooking_time_minutes=30,
            expires_at=datetime.now() + timedelta(hours=4)
        )
        
        from src.domain.model.meal_suggestion import MealType
        
        suggestions = [
            MealSuggestion(
                id="suggestion-1",
                session_id="session-123",
                user_id="user-123",
                meal_name="Meal 1",
                description="Description 1",
                meal_type=MealType.LUNCH,
                macros=MacroEstimate(calories=600, protein=40, carbs=50, fat=20),
                ingredients=[],
                recipe_steps=[],
                prep_time_minutes=20,
                confidence_score=0.9
            ),
            MealSuggestion(
                id="suggestion-2",
                session_id="session-123",
                user_id="user-123",
                meal_name="Meal 2",
                description="Description 2",
                meal_type=MealType.LUNCH,
                macros=MacroEstimate(calories=580, protein=35, carbs=55, fat=18),
                ingredients=[],
                recipe_steps=[],
                prep_time_minutes=25,
                confidence_score=0.85
            ),
            MealSuggestion(
                id="suggestion-3",
                session_id="session-123",
                user_id="user-123",
                meal_name="Meal 3",
                description="Description 3",
                meal_type=MealType.LUNCH,
                macros=MacroEstimate(calories=620, protein=45, carbs=60, fat=22),
                ingredients=[],
                recipe_steps=[],
                prep_time_minutes=30,
                confidence_score=0.88
            )
        ]
        
        result = to_suggestions_list_response(session, suggestions)
        
        assert result.session_id == "session-123"
        assert result.meal_type == "main"
        assert result.meal_portion_type == "regular"
        assert result.target_calories == 600
        assert len(result.suggestions) == 3
        assert result.suggestions[0].id == "suggestion-1"
        assert result.suggestions[1].id == "suggestion-2"
        assert result.suggestions[2].id == "suggestion-3"
        assert result.suggestion_count == 3
        assert result.expires_at == session.expires_at

    def test_to_suggestions_list_response_partial(self):
        """Test converting partial suggestions (1-2) to list response."""
        session = SuggestionSession(
            id="session-456",
            user_id="user-456",
            meal_type="lunch",
            meal_portion_type="main",
            target_calories=500,
            ingredients=[],
            cooking_time_minutes=20,
            expires_at=datetime.now() + timedelta(hours=4)
        )

        from src.domain.model.meal_suggestion import MealType

        # Only 2 suggestions (partial success scenario)
        suggestions = [
            MealSuggestion(
                id="suggestion-1",
                session_id="session-456",
                user_id="user-456",
                meal_name="Meal 1",
                description="Description 1",
                meal_type=MealType.LUNCH,
                macros=MacroEstimate(calories=500, protein=35, carbs=50, fat=18),
                ingredients=[],
                recipe_steps=[],
                prep_time_minutes=20,
                confidence_score=0.9
            ),
            MealSuggestion(
                id="suggestion-2",
                session_id="session-456",
                user_id="user-456",
                meal_name="Meal 2",
                description="Description 2",
                meal_type=MealType.LUNCH,
                macros=MacroEstimate(calories=480, protein=30, carbs=55, fat=15),
                ingredients=[],
                recipe_steps=[],
                prep_time_minutes=25,
                confidence_score=0.85
            ),
        ]

        result = to_suggestions_list_response(session, suggestions)

        assert result.session_id == "session-456"
        assert len(result.suggestions) == 2
        assert result.suggestion_count == 2
        assert result.suggestions[0].id == "suggestion-1"
        assert result.suggestions[1].id == "suggestion-2"


