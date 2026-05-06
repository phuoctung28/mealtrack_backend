import pytest
from unittest.mock import AsyncMock

from src.domain.model.meal_suggestion import (
    Ingredient,
    MacroEstimate,
    MealSuggestion,
    MealType,
    RecipeStep,
)
from src.domain.services.meal_suggestion.deepl_suggestion_translation_service import (
    DeepLSuggestionTranslationService,
)
from src.domain.services.translation.deepl_text_translation_service import DeepLTextTranslationService


@pytest.fixture
def text_translation_service():
    svc = AsyncMock(spec=DeepLTextTranslationService)
    svc.translate_texts = AsyncMock()
    return svc


@pytest.fixture
def service(text_translation_service):
    return DeepLSuggestionTranslationService(text_translation_service)


@pytest.fixture
def suggestion():
    return MealSuggestion(
        id="sug_1",
        session_id="sess_1",
        user_id="user_1",
        meal_name="Grilled Chicken",
        description="Tasty and simple",
        meal_type=MealType.DINNER,
        macros=MacroEstimate(calories=500, protein=40.0, carbs=20.0, fat=25.0),
        ingredients=[
            Ingredient(name="chicken breast", amount=200.0, unit="g"),
            Ingredient(name="olive oil", amount=10.0, unit="ml"),
        ],
        recipe_steps=[
            RecipeStep(step=1, instruction="Heat pan", duration_minutes=2),
            RecipeStep(step=2, instruction="Cook chicken", duration_minutes=10),
        ],
        prep_time_minutes=15,
        confidence_score=0.9,
    )


@pytest.mark.asyncio
async def test_translate_meal_suggestion_skips_english(service, suggestion, text_translation_service):
    result = await service.translate_meal_suggestion(suggestion, "en")
    assert result == suggestion
    text_translation_service.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_translate_meal_suggestion_translates_all_fields(service, suggestion, text_translation_service):
    # Layout: [meal_name, description, *ingredient_names, *step_instructions]
    text_translation_service.translate_texts.return_value = [
        "Gà nướng",
        "Ngon và đơn giản",
        "ức gà",
        "dầu ô liu",
        "Làm nóng chảo",
        "Nấu gà",
    ]

    result = await service.translate_meal_suggestion(suggestion, "vi")

    assert result.meal_name == "Gà nướng"
    assert result.description == "Ngon và đơn giản"
    assert [i.name for i in result.ingredients] == ["ức gà", "dầu ô liu"]
    assert [s.instruction for s in result.recipe_steps] == ["Làm nóng chảo", "Nấu gà"]

    text_translation_service.translate_texts.assert_awaited_once()
    called_texts, called_lang = text_translation_service.translate_texts.call_args.args
    assert called_lang == "vi"
    assert called_texts[0] == "Grilled Chicken"


@pytest.mark.asyncio
async def test_translate_meal_suggestion_pads_when_deepl_returns_short(service, suggestion, text_translation_service):
    # Return fewer items than requested to exercise padding behavior.
    text_translation_service.translate_texts.return_value = ["Gà nướng"]

    result = await service.translate_meal_suggestion(suggestion, "vi")

    assert result.meal_name == "Gà nướng"
    # Remaining fields fall back to originals (padded).
    assert result.description == suggestion.description
    assert result.ingredients[0].name == suggestion.ingredients[0].name


@pytest.mark.asyncio
async def test_translate_meal_suggestion_returns_original_on_exception(service, suggestion, text_translation_service):
    text_translation_service.translate_texts.side_effect = Exception("DeepL down")
    result = await service.translate_meal_suggestion(suggestion, "vi")
    assert result == suggestion


@pytest.mark.asyncio
async def test_translate_meal_suggestions_batch_skips_english(service, suggestion, text_translation_service):
    result = await service.translate_meal_suggestions_batch([suggestion], "en")
    assert result == [suggestion]
    text_translation_service.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_translate_meal_suggestions_batch_translates_each_item(service, suggestion, text_translation_service):
    other = MealSuggestion(
        **{
            **suggestion.__dict__,
            "id": "sug_2",
            "meal_name": "Baked Salmon",
            "ingredients": [Ingredient(name="salmon", amount=100.0, unit="g")],
            "recipe_steps": [RecipeStep(step=1, instruction="Bake", duration_minutes=10)],
        }
    )

    async def translate_side_effect(texts, target_lang):
        # Return "translated:" prefix for determinism.
        return [f"t:{t}" for t in texts]

    text_translation_service.translate_texts.side_effect = translate_side_effect

    result = await service.translate_meal_suggestions_batch([suggestion, other], "vi")

    assert result[0].meal_name.startswith("t:")
    assert result[1].meal_name.startswith("t:")
    assert text_translation_service.translate_texts.await_count == 2


@pytest.mark.asyncio
async def test_translate_meal_suggestions_batch_falls_back_per_item(service, suggestion, text_translation_service):
    other = MealSuggestion(
        **{
            **suggestion.__dict__,
            "id": "sug_2",
            "meal_name": "Baked Salmon",
        }
    )

    async def translate_side_effect(texts, target_lang):
        if texts and texts[0] == "Grilled Chicken":
            raise Exception("fail one")
        return [f"ok:{t}" for t in texts]

    text_translation_service.translate_texts.side_effect = translate_side_effect

    result = await service.translate_meal_suggestions_batch([suggestion, other], "vi")

    assert result[0] == suggestion  # failed item falls back
    assert result[1].meal_name.startswith("ok:")


@pytest.mark.asyncio
async def test_translate_names_skips_english(service, text_translation_service):
    names = ["Grilled Chicken", "Baked Salmon"]
    result = await service.translate_names(names, "en")
    assert result == names
    text_translation_service.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_translate_names_skips_empty_list(service, text_translation_service):
    result = await service.translate_names([], "vi")
    assert result == []
    text_translation_service.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_translate_names_translates_successfully(service, text_translation_service):
    text_translation_service.translate_texts.return_value = ["Gà nướng", "Cá hồi nướng"]
    names = ["Grilled Chicken", "Baked Salmon"]
    result = await service.translate_names(names, "vi")
    assert result == ["Gà nướng", "Cá hồi nướng"]
    text_translation_service.translate_texts.assert_awaited_once_with(names, "vi")


@pytest.mark.asyncio
async def test_translate_names_returns_originals_on_exception(service, text_translation_service):
    text_translation_service.translate_texts.side_effect = Exception("DeepL error")
    names = ["Grilled Chicken", "Baked Salmon"]
    result = await service.translate_names(names, "vi")
    assert result == names

