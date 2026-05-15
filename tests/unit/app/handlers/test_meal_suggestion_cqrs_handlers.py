from unittest.mock import AsyncMock

import pytest

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.meal_suggestion import (
    DiscoverMealsCommand,
    GenerateMealRecipesCommand,
)
from src.app.handlers.command_handlers.meal_suggestion import (
    DiscoverMealsCommandHandler,
    GenerateMealRecipesCommandHandler,
)
from src.domain.model.meal_suggestion import SuggestionSession
from src.domain.model.meal_suggestion.meal_suggestion import (
    Ingredient,
    MacroEstimate,
    MealSuggestion,
    MealType,
    RecipeStep,
)


@pytest.mark.asyncio
async def test_discover_meals_handler_delegates_to_orchestration_service():
    service = AsyncMock()
    session = SuggestionSession(
        id="sess-discovery",
        user_id="user-1",
        meal_type="lunch",
        meal_portion_type="main",
        target_calories=500,
        ingredients=["tofu"],
        cooking_time_minutes=20,
    )
    meals = [{"id": "disc_a", "english_name": "Tofu Bowl", "calories": 450}]
    service.generate_discovery.return_value = (session, meals)

    result = await DiscoverMealsCommandHandler(service).handle(
        DiscoverMealsCommand(
            user_id="user-1",
            meal_type="lunch",
            meal_portion_type="main",
            ingredients=["tofu"],
            time_available_minutes=20,
            session_id=None,
            language="en",
            cuisine_region="japanese",
            calorie_target=450,
            protein_target=35,
            carbs_target=40,
            fat_target=14,
            count=6,
        )
    )

    assert result == (session, meals)
    service.generate_discovery.assert_awaited_once_with(
        user_id="user-1",
        meal_type="lunch",
        meal_portion_type="main",
        ingredients=["tofu"],
        cooking_time_minutes=20,
        session_id=None,
        language="en",
        cuisine_region="japanese",
        calorie_target_override=450,
        protein_target=35,
        carbs_target=40,
        fat_target=14,
        count=6,
    )


@pytest.mark.asyncio
async def test_generate_meal_recipes_handler_prefers_session_discovery_meals():
    discovery_session = SuggestionSession(
        id="sess-discovery",
        user_id="user-1",
        meal_type="lunch",
        meal_portion_type="main",
        target_calories=500,
        ingredients=["carp"],
        cooking_time_minutes=30,
        discovery_meals=[
            {
                "id": "disc_a",
                "name": "Ginger Carp",
                "english_name": "Ginger Carp",
                "calories": 300,
                "protein": 32,
                "carbs": 18,
                "fat": 10,
            },
            {
                "id": "disc_b",
                "name": "Grilled Carp",
                "english_name": "Grilled Carp",
                "calories": 350,
                "protein": 35,
                "carbs": 20,
                "fat": 12,
            },
        ],
    )
    service = AsyncMock()
    service._repo.get_session.return_value = discovery_session
    service._recipe_generator.generate_selected_recipes.return_value = [
        _recipe("r1", "Grilled Carp", 350),
        _recipe("r2", "Ginger Carp", 300),
    ]

    recipes = await GenerateMealRecipesCommandHandler(service).handle(
        GenerateMealRecipesCommand(
            user_id="user-1",
            meal_type="lunch",
            language="en",
            session_id="sess-discovery",
            selected_meal_ids=["disc_b", "disc_a"],
            selected_meals=[
                {
                    "id": "disc_b",
                    "meal_name": "Client stale name",
                    "english_name": "Client stale name",
                    "macros": {
                        "calories": 999,
                        "protein": 1,
                        "carbs": 1,
                        "fat": 1,
                    },
                }
            ],
        )
    )

    assert [recipe.meal_name for recipe in recipes] == ["Grilled Carp", "Ginger Carp"]
    call = service._recipe_generator.generate_selected_recipes.await_args
    recipe_session, selected_meals = call.args
    assert recipe_session.target_calories == 350
    assert [meal["id"] for meal in selected_meals] == ["disc_b", "disc_a"]
    assert selected_meals[0]["calories"] == 350


@pytest.mark.asyncio
async def test_generate_meal_recipes_handler_uses_client_selected_meals_if_session_expired():
    service = AsyncMock()
    service._repo.get_session.return_value = None
    service._recipe_generator.generate_selected_recipes.return_value = [
        _recipe("r1", "Ginger Carp", 300)
    ]

    recipes = await GenerateMealRecipesCommandHandler(service).handle(
        GenerateMealRecipesCommand(
            user_id="user-1",
            meal_type="lunch",
            language="en",
            session_id="expired",
            selected_meal_ids=["disc_a"],
            selected_meals=[
                {
                    "id": "disc_a",
                    "meal_name": "Ginger Carp",
                    "english_name": "Ginger Carp",
                    "macros": {
                        "calories": 300,
                        "protein": 32,
                        "carbs": 18,
                        "fat": 10,
                    },
                }
            ],
        )
    )

    assert [recipe.meal_name for recipe in recipes] == ["Ginger Carp"]
    _session, selected_meals = (
        service._recipe_generator.generate_selected_recipes.await_args.args
    )
    assert selected_meals == [
        {
            "id": "disc_a",
            "name": "Ginger Carp",
            "english_name": "Ginger Carp",
            "calories": 300,
            "protein": 32,
            "carbs": 18,
            "fat": 10,
        }
    ]


@pytest.mark.asyncio
async def test_generate_meal_recipes_handler_rejects_missing_selected_ids():
    discovery_session = SuggestionSession(
        id="sess-discovery",
        user_id="user-1",
        meal_type="lunch",
        meal_portion_type="main",
        target_calories=500,
        ingredients=[],
        cooking_time_minutes=None,
        discovery_meals=[],
    )
    service = AsyncMock()
    service._repo.get_session.return_value = discovery_session

    with pytest.raises(ValidationException) as exc:
        await GenerateMealRecipesCommandHandler(service).handle(
            GenerateMealRecipesCommand(
                user_id="user-1",
                meal_type="lunch",
                language="en",
                session_id="sess-discovery",
                selected_meal_ids=["disc_missing"],
            )
        )

    assert exc.value.error_code == "SELECTED_MEAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_generate_meal_recipes_handler_rejects_missing_session_without_client_meals():
    service = AsyncMock()
    service._repo.get_session.return_value = None

    with pytest.raises(ResourceNotFoundException) as exc:
        await GenerateMealRecipesCommandHandler(service).handle(
            GenerateMealRecipesCommand(
                user_id="user-1",
                meal_type="lunch",
                language="en",
                session_id="expired",
                selected_meal_ids=["disc_a"],
            )
        )

    assert exc.value.error_code == "DISCOVERY_SESSION_NOT_FOUND"


def _recipe(recipe_id: str, name: str, calories: float) -> MealSuggestion:
    return MealSuggestion(
        id=recipe_id,
        session_id="recipe-session",
        user_id="user-1",
        meal_name=name,
        description="",
        meal_type=MealType.LUNCH,
        macros=MacroEstimate(calories=calories, protein=30, carbs=20, fat=10),
        ingredients=[Ingredient(name="carp", amount=120, unit="g")],
        recipe_steps=[RecipeStep(step=1, instruction="Cook.", duration_minutes=15)],
        prep_time_minutes=20,
        confidence_score=0.9,
    )
