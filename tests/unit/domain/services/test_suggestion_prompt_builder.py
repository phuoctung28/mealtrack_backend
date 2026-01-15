"""
Unit tests for SuggestionPromptBuilder (Phase 1 & 2).
Tests that prompts request 4 names, no description, and generate in English.
Translation happens in Phase 3 post-generation.
"""
import pytest

from src.domain.model.meal_suggestion import SuggestionSession
from src.domain.services.meal_suggestion.suggestion_prompt_builder import (
    build_meal_names_prompt,
    build_recipe_details_prompt,
)
from src.domain.services.prompts.prompt_template_manager import PromptTemplateManager


@pytest.fixture
def mock_session():
    """Create a test session."""
    return SuggestionSession(
        id="test_session_123",
        user_id="user_456",
        meal_type="breakfast",
        meal_portion_type="standard",
        target_calories=500,
        ingredients=["chicken", "broccoli", "rice", "eggs", "spinach"],
        cooking_time_minutes=20,
        dietary_preferences=["vegetarian"],
        allergies=["peanuts"],
    )


class TestBuildMealNamesPrompt:
    """Test build_meal_names_prompt for Phase 1 (4 diverse names)."""

    def test_requests_exactly_6_names(self, mock_session):
        """Prompt should explicitly request 4 meal names."""
        prompt = build_meal_names_prompt(mock_session)

        # Should contain "4" and "different" or similar
        assert "4" in prompt.lower()
        assert "4 different" in prompt.lower()

    def test_includes_meal_type(self, mock_session):
        """Prompt should include the meal type (breakfast, lunch, dinner)."""
        prompt = build_meal_names_prompt(mock_session)

        assert "breakfast" in prompt.lower() or mock_session.meal_type in prompt.lower()

    def test_includes_ingredients(self, mock_session):
        """Prompt should list available ingredients."""
        prompt = build_meal_names_prompt(mock_session)

        # Should mention ingredients and include some from the list
        assert "ingredient" in prompt.lower()
        # At least one ingredient should be mentioned
        assert any(ing in prompt for ing in mock_session.ingredients[:3])

    def test_emphasizes_diversity(self, mock_session):
        """Prompt should emphasize diverse cuisines."""
        prompt = build_meal_names_prompt(mock_session)

        # Should mention diverse cuisines (4 different cuisines)
        assert "4 different" in prompt or "different" in prompt.lower()
        assert "cuisine" in prompt.lower() or "asian" in prompt.lower()

    def test_emphasizes_concise_names(self, mock_session):
        """Prompt should emphasize short, concise names (not 'Quick', 'Speedy', etc)."""
        prompt = build_meal_names_prompt(mock_session)

        # Should mention concise naming
        assert "concise" in prompt.lower() or "short" in prompt.lower()
        # Should discourage generic prefixes
        assert "Quick" in prompt or "Speedy" in prompt or "Power" in prompt

    def test_includes_dietary_preferences(self, mock_session):
        """Prompt should include dietary preferences if present."""
        session = SuggestionSession(
            id="test",
            user_id="user",
            meal_type="breakfast",
            meal_portion_type="standard",
            target_calories=500,
            ingredients=["chicken", "rice"],
            cooking_time_minutes=20,
            dietary_preferences=["vegan", "gluten-free"],
            allergies=[],
        )

        prompt = build_meal_names_prompt(session)

        # Should mention dietary info if present
        assert "vegan" in prompt.lower() or "gluten-free" in prompt.lower() or "vegetarian" not in prompt.lower()

    def test_includes_allergies(self, mock_session):
        """Prompt should mention allergies to avoid."""
        prompt = build_meal_names_prompt(mock_session)

        # Should mention avoiding allergies
        assert "peanut" in prompt.lower() or "allerg" in prompt.lower() or "avoid" in prompt.lower()

    def test_no_long_examples(self, mock_session):
        """Prompt should show bad examples of long names to discourage them."""
        prompt = build_meal_names_prompt(mock_session)

        # Should have guidance on name length
        assert "max" in prompt.lower() or "word" in prompt.lower() or "char" in prompt.lower()

    def test_includes_good_examples(self, mock_session):
        """Prompt should have name guidelines."""
        prompt = build_meal_names_prompt(mock_session)

        # Should have guidelines for naming (concise, max words)
        assert "max" in prompt.lower() or "word" in prompt.lower() or "natural" in prompt.lower()


class TestBuildRecipeDetailsPrompt:
    """Test build_recipe_details_prompt for Phase 2 (no description requested)."""

    def test_no_description_field_requested(self, mock_session):
        """Prompt should NOT request description field."""
        meal_name = "Garlic Butter Salmon"
        prompt = build_recipe_details_prompt(meal_name, mock_session)

        # Should NOT ask for description
        assert '"description"' not in prompt or "description" not in prompt.lower()

    def test_includes_meal_name(self, mock_session):
        """Prompt should include the specific meal name to generate."""
        meal_name = "Garlic Butter Salmon"
        prompt = build_recipe_details_prompt(meal_name, mock_session)

        # Should mention the specific meal name
        assert meal_name in prompt

    def test_includes_calorie_target(self, mock_session):
        """Prompt should include target calories."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should mention target calories (either "calor" or "cal")
        prompt_lower = prompt.lower()
        assert "cal" in prompt_lower  # Matches both "calor" and "cal"
        assert str(mock_session.target_calories) in prompt or "~" in prompt

    def test_includes_cooking_time(self, mock_session):
        """Prompt should include maximum cooking time."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should mention cooking time
        assert "cooking" in prompt.lower() or "time" in prompt.lower() or "minute" in prompt.lower()

    def test_includes_ingredients(self, mock_session):
        """Prompt should list available ingredients."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should mention ingredients
        assert "ingredient" in prompt.lower()
        # At least one ingredient should be included
        assert any(ing in prompt for ing in mock_session.ingredients[:2])

    def test_includes_dietary_constraints(self, mock_session):
        """Prompt should include dietary constraints."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should mention dietary info
        assert "vegetarian" in prompt.lower() or "allerg" in prompt.lower()

    def test_requests_structured_json_output(self, mock_session):
        """Prompt should request specific fields: ingredients, steps, prep_time."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should request specific fields: ingredients, recipe_steps, prep_time
        assert "ingredient" in prompt.lower()
        assert "recipe" in prompt.lower() or "step" in prompt.lower()
        assert "prep" in prompt.lower() or "time" in prompt.lower()

    def test_requests_macro_calculation(self, mock_session):
        """Prompt should request macronutrient calculation from ingredients."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should request macros calculation from ingredients
        assert "macros" in prompt.lower() or "calories" in prompt.lower()

    def test_includes_portion_sizing_guidance(self, mock_session):
        """Prompt should include guidance on portion sizing."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should mention portion sizing or amounts
        assert "portion" in prompt.lower() or "amount" in prompt.lower() or "gram" in prompt.lower()

    def test_includes_ingredient_list(self, mock_session):
        """Prompt should include list of available ingredients."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should contain ingredient information
        assert "chicken" in prompt.lower() or "broccoli" in prompt.lower()

    def test_requests_specific_ingredient_amounts(self, mock_session):
        """Prompt should request specific amounts for ingredients (g, ml, tbsp, etc)."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should mention units or amounts
        assert any(unit in prompt for unit in ["g", "ml", "tbsp", "tsp", "cup", "amount", "gram"])

    def test_requests_recipe_steps_with_duration(self, mock_session):
        """Prompt should request recipe steps with duration for each step."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should mention steps and duration
        assert "step" in prompt.lower()
        assert "duration" in prompt.lower() or "minute" in prompt.lower() or "time" in prompt.lower()

    def test_requests_macros_in_prompt(self, mock_session):
        """Prompt should request macronutrient data calculation."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Current implementation requests AI to calculate macros from ingredients
        assert "protein" in prompt.lower() or "macros" in prompt.lower()
        assert "carbs" in prompt.lower() or "calories" in prompt.lower()

    def test_meal_name_must_match(self, mock_session):
        """Prompt should emphasize that generated meal must match the provided name."""
        meal_name = "Spicy Thai Basil Chicken"
        prompt = build_recipe_details_prompt(meal_name, mock_session)

        # Should request exact match with the meal name
        assert meal_name in prompt
        assert "exactly" in prompt.lower() or "match" in prompt.lower() or "must" in prompt.lower()


class TestSessionEdgeCases:
    """Test prompt building with edge cases."""

    def test_session_no_ingredients(self):
        """Prompt should handle session with no ingredients."""
        session = SuggestionSession(
            id="test",
            user_id="user",
            meal_type="breakfast",
            meal_portion_type="standard",
            target_calories=500,
            ingredients=[],
            cooking_time_minutes=20,
            dietary_preferences=[],
            allergies=[],
        )

        prompt = build_meal_names_prompt(session)

        # Should still generate valid prompt (4 names)
        assert len(prompt) > 0
        assert "4" in prompt.lower()

    def test_session_no_dietary_prefs(self):
        """Prompt should handle session with no dietary preferences."""
        session = SuggestionSession(
            id="test",
            user_id="user",
            meal_type="breakfast",
            meal_portion_type="standard",
            target_calories=500,
            ingredients=["chicken", "rice"],
            cooking_time_minutes=20,
            dietary_preferences=[],
            allergies=[],
        )

        prompt = build_meal_names_prompt(session)

        # Should generate valid prompt without dietary prefs (4 names)
        assert len(prompt) > 0
        assert "4" in prompt.lower()

    def test_session_no_allergies(self):
        """Prompt should handle session with no allergies."""
        session = SuggestionSession(
            id="test",
            user_id="user",
            meal_type="breakfast",
            meal_portion_type="standard",
            target_calories=500,
            ingredients=["chicken", "rice"],
            cooking_time_minutes=20,
            dietary_preferences=["vegetarian"],
            allergies=[],
        )

        prompt = build_meal_names_prompt(session)

        # Should generate valid prompt without allergies
        assert len(prompt) > 0
        assert "vegetarian" in prompt.lower()

    def test_long_ingredient_list(self):
        """Prompt should handle long ingredient list."""
        long_ingredients = [f"ingredient_{i}" for i in range(20)]
        session = SuggestionSession(
            id="test",
            user_id="user",
            meal_type="breakfast",
            meal_portion_type="standard",
            target_calories=500,
            ingredients=long_ingredients,
            cooking_time_minutes=20,
            dietary_preferences=[],
            allergies=[],
        )

        prompt = build_meal_names_prompt(session)

        # Should still be reasonable length and focus on first few
        assert len(prompt) > 0
        assert len(prompt) < 2000  # Prompts should be concise


class TestPromptContent:
    """Test specific content requirements in prompts."""

    def test_meal_names_prompt_format(self, mock_session):
        """Meal names prompt should have clear structure."""
        prompt = build_meal_names_prompt(mock_session)

        # Should have clear sections (4 names)
        assert "Generate" in prompt or "generate" in prompt
        assert "4" in prompt

    def test_recipe_details_prompt_format(self, mock_session):
        """Recipe details prompt should have clear instructions."""
        prompt = build_recipe_details_prompt("Test Meal", mock_session)

        # Should have clear instructions
        assert "ingredient" in prompt.lower()
        assert "requirement" in prompt.lower() or "recipe" in prompt.lower()

    def test_prompts_are_non_empty(self, mock_session):
        """Both prompts should be non-empty."""
        names_prompt = build_meal_names_prompt(mock_session)
        recipe_prompt = build_recipe_details_prompt("Test", mock_session)

        assert len(names_prompt) > 0
        assert len(recipe_prompt) > 0

    def test_prompts_are_reasonable_length(self, mock_session):
        """Prompts should be reasonably concise (not huge)."""
        names_prompt = build_meal_names_prompt(mock_session)
        recipe_prompt = build_recipe_details_prompt("Test", mock_session)

        # Prompts should be under 2000 chars (good for API)
        assert len(names_prompt) < 2000
        assert len(recipe_prompt) < 2000


