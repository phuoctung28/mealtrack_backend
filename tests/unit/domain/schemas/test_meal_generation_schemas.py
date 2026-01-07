"""
Unit tests for meal generation schemas (Phase 01 & 02 optimization).
Tests validate 6-name generation and removal of description field.
"""
import pytest
from pydantic import ValidationError

from src.domain.schemas.meal_generation_schemas import (
    MealNamesResponse,
    RecipeDetailsResponse,
    IngredientItem,
    RecipeStepItem,
)


class TestMealNamesResponse:
    """Test MealNamesResponse validation for 4 diverse names."""

    def test_valid_4_names(self):
        """Valid: exactly 4 meal names."""
        response = MealNamesResponse(
            meal_names=[
                "Garlic Butter Salmon",
                "Spicy Thai Basil Chicken",
                "Mediterranean Lamb Bowl",
                "Teriyaki Beef Stir-fry"
            ]
        )
        assert len(response.meal_names) == 4
        assert all(isinstance(name, str) for name in response.meal_names)

    def test_rejects_3_names(self):
        """Invalid: only 3 names (need 4)."""
        with pytest.raises(ValidationError) as exc_info:
            MealNamesResponse(
                meal_names=["Meal 1", "Meal 2", "Meal 3"]
            )
        # Verify min_length validation error
        assert "at least 4 items" in str(exc_info.value).lower()

    def test_rejects_5_names(self):
        """Invalid: 5 names (one more than 4)."""
        with pytest.raises(ValidationError):
            MealNamesResponse(
                meal_names=["M1", "M2", "M3", "M4", "M5"]
            )

    def test_rejects_2_names(self):
        """Invalid: 2 names (two short of 4)."""
        with pytest.raises(ValidationError):
            MealNamesResponse(
                meal_names=["M1", "M2"]
            )

    def test_truncates_long_names(self):
        """Long names are truncated to 60 chars."""
        long_name = "X" * 100  # Well over 60 chars
        response = MealNamesResponse(
            meal_names=[long_name] * 4
        )
        # Should truncate to max 60 chars with "..." suffix
        assert len(response.meal_names[0]) <= 60

    def test_accepts_diverse_cuisines(self):
        """Accepts diverse cuisine types."""
        diverse_names = [
            "Thai Green Curry Chicken",      # Asian
            "Mediterranean Feta Salad",      # Mediterranean
            "Mexican Chipotle Bowl",         # Latin
            "Indian Tandoori Fish"           # Indian
        ]
        response = MealNamesResponse(meal_names=diverse_names)
        assert len(response.meal_names) == 4


class TestRecipeDetailsResponse:
    """Test RecipeDetailsResponse validation (description field removed in Phase 01)."""

    def test_valid_recipe_no_description(self):
        """Valid: recipe with ingredients, steps, prep_time (NO description)."""
        response = RecipeDetailsResponse(
            ingredients=[
                IngredientItem(name="Chicken breast", amount=200, unit="g"),
                IngredientItem(name="Broccoli", amount=150, unit="g"),
                IngredientItem(name="Olive oil", amount=2, unit="tbsp"),
            ],
            recipe_steps=[
                RecipeStepItem(step=1, instruction="Heat pan", duration_minutes=2),
                RecipeStepItem(step=2, instruction="Cook chicken", duration_minutes=10),
                RecipeStepItem(step=3, instruction="Add broccoli", duration_minutes=5),
            ],
            prep_time_minutes=20
        )
        assert not hasattr(response, 'description'), "Response should not have description field"
        assert len(response.ingredients) == 3
        assert len(response.recipe_steps) == 3
        assert response.prep_time_minutes == 20

    def test_rejects_missing_ingredients(self):
        """Invalid: missing ingredients."""
        with pytest.raises(ValidationError):
            RecipeDetailsResponse(
                ingredients=[],  # Empty
                recipe_steps=[
                    RecipeStepItem(step=1, instruction="Test", duration_minutes=5),
                ],
                prep_time_minutes=15
            )

    def test_rejects_missing_recipe_steps(self):
        """Invalid: missing recipe steps."""
        with pytest.raises(ValidationError):
            RecipeDetailsResponse(
                ingredients=[
                    IngredientItem(name="Chicken", amount=200, unit="g"),
                ],
                recipe_steps=[],  # Empty
                prep_time_minutes=15
            )

    def test_validates_ingredient_count_min_3(self):
        """Validates minimum 3 ingredients."""
        # 2 ingredients should fail (min_length=3)
        with pytest.raises(ValidationError):
            RecipeDetailsResponse(
                ingredients=[
                    IngredientItem(name="A", amount=1, unit="g"),
                    IngredientItem(name="B", amount=2, unit="g"),
                ],
                recipe_steps=[
                    RecipeStepItem(step=1, instruction="Mix", duration_minutes=5),
                ],
                prep_time_minutes=10
            )

    def test_validates_ingredient_count_max_8(self):
        """Validates maximum 8 ingredients."""
        # 9 ingredients should fail (max_length=8)
        with pytest.raises(ValidationError):
            RecipeDetailsResponse(
                ingredients=[
                    IngredientItem(name=f"Ingredient {i}", amount=100, unit="g")
                    for i in range(9)
                ],
                recipe_steps=[
                    RecipeStepItem(step=1, instruction="Mix all", duration_minutes=10),
                ],
                prep_time_minutes=20
            )

    def test_validates_recipe_step_count_min_2(self):
        """Validates minimum 2 recipe steps."""
        # 1 step should fail (min_length=2)
        with pytest.raises(ValidationError):
            RecipeDetailsResponse(
                ingredients=[
                    IngredientItem(name="A", amount=1, unit="g"),
                    IngredientItem(name="B", amount=2, unit="g"),
                    IngredientItem(name="C", amount=3, unit="g"),
                ],
                recipe_steps=[
                    RecipeStepItem(step=1, instruction="Do something", duration_minutes=5),
                ],
                prep_time_minutes=10
            )

    def test_validates_recipe_step_count_max_6(self):
        """Validates maximum 6 recipe steps."""
        # 7 steps should fail (max_length=6)
        with pytest.raises(ValidationError):
            RecipeDetailsResponse(
                ingredients=[
                    IngredientItem(name=f"Ing {i}", amount=100, unit="g")
                    for i in range(3)
                ],
                recipe_steps=[
                    RecipeStepItem(step=i, instruction=f"Step {i}", duration_minutes=5)
                    for i in range(1, 8)  # 7 steps
                ],
                prep_time_minutes=30
            )

    def test_validates_prep_time_min_5(self):
        """Validates minimum prep time of 5 minutes."""
        with pytest.raises(ValidationError):
            RecipeDetailsResponse(
                ingredients=[
                    IngredientItem(name="A", amount=1, unit="g"),
                    IngredientItem(name="B", amount=2, unit="g"),
                    IngredientItem(name="C", amount=3, unit="g"),
                ],
                recipe_steps=[
                    RecipeStepItem(step=1, instruction="Mix", duration_minutes=2),
                    RecipeStepItem(step=2, instruction="Cook", duration_minutes=2),
                ],
                prep_time_minutes=4  # Too short
            )

    def test_validates_prep_time_max_120(self):
        """Validates maximum prep time of 120 minutes."""
        with pytest.raises(ValidationError):
            RecipeDetailsResponse(
                ingredients=[
                    IngredientItem(name="A", amount=1, unit="g"),
                    IngredientItem(name="B", amount=2, unit="g"),
                    IngredientItem(name="C", amount=3, unit="g"),
                ],
                recipe_steps=[
                    RecipeStepItem(step=1, instruction="Mix", duration_minutes=60),
                    RecipeStepItem(step=2, instruction="Cook", duration_minutes=60),
                ],
                prep_time_minutes=121  # Too long
            )

    def test_valid_edge_case_min_values(self):
        """Valid: minimum allowed values (3 ingredients, 2 steps, 5 min prep)."""
        response = RecipeDetailsResponse(
            ingredients=[
                IngredientItem(name="A", amount=1, unit="g"),
                IngredientItem(name="B", amount=2, unit="g"),
                IngredientItem(name="C", amount=3, unit="g"),
            ],
            recipe_steps=[
                RecipeStepItem(step=1, instruction="Do A", duration_minutes=2),
                RecipeStepItem(step=2, instruction="Do B", duration_minutes=3),
            ],
            prep_time_minutes=5
        )
        assert len(response.ingredients) == 3
        assert len(response.recipe_steps) == 2
        assert response.prep_time_minutes == 5

    def test_valid_edge_case_max_values(self):
        """Valid: maximum allowed values (8 ingredients, 6 steps, 120 min prep)."""
        response = RecipeDetailsResponse(
            ingredients=[
                IngredientItem(name=f"Ing {i}", amount=100 + i, unit="g")
                for i in range(8)
            ],
            recipe_steps=[
                RecipeStepItem(step=i, instruction=f"Step {i}", duration_minutes=20)
                for i in range(1, 7)  # 6 steps
            ],
            prep_time_minutes=120
        )
        assert len(response.ingredients) == 8
        assert len(response.recipe_steps) == 6
        assert response.prep_time_minutes == 120


class TestIngredientItem:
    """Test IngredientItem validation."""

    def test_valid_ingredient(self):
        """Valid ingredient with name, amount, unit."""
        item = IngredientItem(
            name="Chicken breast",
            amount=200,
            unit="g"
        )
        assert item.name == "Chicken breast"
        assert item.amount == 200
        assert item.unit == "g"

    def test_rejects_zero_amount(self):
        """Invalid: zero or negative amount."""
        with pytest.raises(ValidationError):
            IngredientItem(name="Chicken", amount=0, unit="g")

    def test_rejects_negative_amount(self):
        """Invalid: negative amount."""
        with pytest.raises(ValidationError):
            IngredientItem(name="Chicken", amount=-100, unit="g")

    def test_accepts_decimal_amount(self):
        """Valid: decimal amounts (e.g., 1.5 cups)."""
        item = IngredientItem(name="Flour", amount=1.5, unit="cup")
        assert item.amount == 1.5


class TestRecipeStepItem:
    """Test RecipeStepItem validation."""

    def test_valid_step(self):
        """Valid recipe step."""
        item = RecipeStepItem(
            step=1,
            instruction="Heat the pan",
            duration_minutes=5
        )
        assert item.step == 1
        assert item.instruction == "Heat the pan"
        assert item.duration_minutes == 5

    def test_rejects_zero_step_number(self):
        """Invalid: step number must be >= 1."""
        with pytest.raises(ValidationError):
            RecipeStepItem(step=0, instruction="Test", duration_minutes=5)

    def test_rejects_negative_duration(self):
        """Invalid: negative duration."""
        with pytest.raises(ValidationError):
            RecipeStepItem(step=1, instruction="Test", duration_minutes=-5)

    def test_accepts_zero_duration(self):
        """Valid: zero duration (instant steps)."""
        item = RecipeStepItem(step=1, instruction="Serve", duration_minutes=0)
        assert item.duration_minutes == 0

    def test_sequential_steps(self):
        """Valid: sequential step numbers."""
        steps = [
            RecipeStepItem(step=1, instruction="Step 1", duration_minutes=5),
            RecipeStepItem(step=2, instruction="Step 2", duration_minutes=10),
            RecipeStepItem(step=3, instruction="Step 3", duration_minutes=8),
        ]
        assert len(steps) == 3
        assert [s.step for s in steps] == [1, 2, 3]
