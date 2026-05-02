import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.domain.model.meal.meal import Meal, MealStatus
from src.domain.model.meal.meal_image import MealImage
from src.domain.model.meal.meal_translation_domain_models import MealTranslation
from src.domain.model.nutrition.macros import Macros
from src.domain.model.nutrition.nutrition import FoodItem
from src.domain.services.meal_analysis.deepl_meal_translation_service import (
    DeepLMealTranslationService,
)


@pytest.fixture
def meal():
    return Meal(
        meal_id=str(uuid4()),
        user_id=str(uuid4()),
        status=MealStatus.PROCESSING,
        created_at=datetime.utcnow(),
        image=MealImage(
            image_id=str(uuid4()), format="jpeg", size_bytes=1024, url="https://x/y.jpg"
        ),
    )


@pytest.fixture
def food_items():
    return [
        FoodItem(
            id=str(uuid4()),
            name="Chicken breast",
            quantity=150,
            unit="g",
            macros=Macros(protein=31, carbs=0, fat=3.6),
        ),
        FoodItem(
            id=str(uuid4()),
            name="Brown rice",
            quantity=200,
            unit="g",
            macros=Macros(protein=5, carbs=46, fat=1.8),
        ),
    ]


@pytest.fixture
def repo():
    r = Mock()
    r.get_by_meal_and_language = Mock(return_value=None)
    r.save = Mock(side_effect=lambda t: t)
    return r


@pytest.fixture
def deepl_port():
    p = AsyncMock()
    p.translate_texts = AsyncMock()
    return p


@pytest.fixture
def service(repo, deepl_port):
    return DeepLMealTranslationService(translation_repo=repo, deepl_port=deepl_port)


@pytest.mark.asyncio
async def test_translate_meal_skips_english(
    service, meal, food_items, deepl_port, repo
):
    result = await service.translate_meal(meal, "Grilled chicken", food_items, "en")
    assert result is None
    deepl_port.translate_texts.assert_not_called()
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_translate_meal_uses_cache_when_fully_cached(
    service, meal, food_items, deepl_port, repo
):
    cached = MealTranslation(
        meal_id=meal.meal_id,
        language="vi",
        dish_name="cached",
        food_items=[],
        meal_instruction=[{"instruction": "x", "duration_minutes": None}],
        meal_ingredients=["a", "b"],
    )
    repo.get_by_meal_and_language.return_value = cached

    result = await service.translate_meal(
        meal, "Grilled chicken", food_items, "vi", instructions=["Step"]
    )

    assert result == cached
    deepl_port.translate_texts.assert_not_called()
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_translate_meal_calls_deepl_and_saves(
    service, meal, food_items, deepl_port, repo
):
    deepl_port.translate_texts.return_value = [
        "Gà nướng",  # dish
        "Ức gà",  # ingredient 1
        "Cơm gạo lứt",  # ingredient 2
        "Bước 1",  # instruction
    ]

    result = await service.translate_meal(
        meal,
        dish_name="Grilled chicken",
        food_items=food_items,
        target_language="vi",
        instructions=["Step 1"],
    )

    assert result is not None
    assert result.dish_name == "Gà nướng"
    assert result.meal_ingredients == ["Ức gà", "Cơm gạo lứt"]
    assert result.meal_instruction == [
        {"instruction": "Bước 1", "duration_minutes": None}
    ]
    repo.save.assert_called_once()
    deepl_port.translate_texts.assert_awaited_once()


@pytest.mark.asyncio
async def test_translate_meal_normalizes_instruction_dicts(
    service, meal, food_items, deepl_port
):
    deepl_port.translate_texts.return_value = [
        "Gà nướng",
        "Ức gà",
        "Cơm gạo lứt",
        "Làm nóng chảo",
        "Nấu gà",
    ]

    result = await service.translate_meal(
        meal,
        dish_name="Grilled chicken",
        food_items=food_items,
        target_language="vi",
        instructions=[
            {"instruction": "Heat pan", "duration_minutes": 2},
            {"instruction": "Cook chicken", "duration_minutes": 10},
        ],
    )

    assert result.meal_instruction == [
        {"instruction": "Làm nóng chảo", "duration_minutes": 2},
        {"instruction": "Nấu gà", "duration_minutes": 10},
    ]


@pytest.mark.asyncio
async def test_translate_meal_pads_when_deepl_returns_short(
    service, meal, food_items, deepl_port
):
    # Only dish name returned, rest should be padded with originals.
    deepl_port.translate_texts.return_value = ["Gà nướng"]

    result = await service.translate_meal(
        meal,
        dish_name="Grilled chicken",
        food_items=food_items,
        target_language="vi",
        instructions=["Step 1"],
    )

    assert result.dish_name == "Gà nướng"
    # Ingredients padded to original ingredient names
    assert result.meal_ingredients == [fi.name for fi in food_items]
    # Instruction padded to original
    assert result.meal_instruction == [
        {"instruction": "Step 1", "duration_minutes": None}
    ]


@pytest.mark.asyncio
async def test_translate_meal_returns_none_on_exception(
    service, meal, food_items, deepl_port, repo
):
    deepl_port.translate_texts.side_effect = Exception("DeepL down")

    result = await service.translate_meal(
        meal,
        dish_name="Grilled chicken",
        food_items=food_items,
        target_language="vi",
        instructions=["Step 1"],
    )

    assert result is None
    repo.save.assert_not_called()
