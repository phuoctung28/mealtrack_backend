"""
Unit tests for food database feature: search, details, and manual meal creation.
"""
import pytest

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


# Stub service and cache for tests
class StubFoodDataService:
    async def search_foods(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        return [
            {
                "fdcId": 12345,
                "description": "Chicken, breast, grilled",
                "brandOwner": None,
                "dataType": "Foundation",
                "publishedDate": "2020-01-01"
            }
        ]

    async def get_food_details(self, fdc_id: int) -> Dict[str, Any]:
        # Return USDA-style details with nutrient IDs
        return {
            "fdcId": fdc_id,
            "description": "Chicken, breast, grilled",
            "brandOwner": None,
            "servingSize": 100.0,
            "servingSizeUnit": "g",
            "foodNutrients": [
                {"nutrient": {"id": 1008, "name": "Energy", "unitName": "kcal"}, "amount": 165.0},
                {"nutrient": {"id": 1003, "name": "Protein", "unitName": "g"}, "amount": 31.0},
                {"nutrient": {"id": 1005, "name": "Carbohydrate", "unitName": "g"}, "amount": 0.0},
                {"nutrient": {"id": 1004, "name": "Total lipid (fat)", "unitName": "g"}, "amount": 3.6},
            ],
            "foodPortions": [
                {"measureUnit": {"name": "g"}, "gramWeight": 100.0, "modifier": "serving"},
            ],
        }


class NoopFoodCacheService:
    async def get_cached_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        return None

    async def cache_search(self, query: str, results: List[Dict[str, Any]], ttl: int = 3600):
        return None

    async def get_cached_food(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        return None

    async def cache_food(self, fdc_id: int, food_data: Dict[str, Any], ttl: int = 86400):
        return None


# Lightweight in-memory meal repository stub
class InMemoryMealRepository:
    def __init__(self):
        self._store: Dict[str, Any] = {}

    def save(self, meal):
        self._store[meal.meal_id] = meal
        return meal

    def find_by_id(self, meal_id: str):
        return self._store.get(meal_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_foods_query_handler_returns_mapped_results(monkeypatch):
    from src.app.queries.food.search_foods_query import SearchFoodsQuery
    from src.app.handlers.query_handlers import SearchFoodsQueryHandler
    from src.domain.services.food_mapping_service import FoodMappingService

    handler = SearchFoodsQueryHandler(
        food_data_service=StubFoodDataService(),
        cache_service=NoopFoodCacheService(),
        mapping_service=FoodMappingService(),
    )

    result = await handler.handle(SearchFoodsQuery(query="chicken", limit=10))

    assert isinstance(result, dict)
    assert "results" in result
    assert len(result["results"]) == 1
    item = result["results"][0]
    assert item["fdc_id"] == 12345
    assert item["name"].lower().startswith("chicken")
    assert item["data_type"] == "Foundation"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_food_details_query_handler_maps_nutrients():
    from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery
    from src.app.handlers.query_handlers import GetFoodDetailsQueryHandler
    from src.domain.services.food_mapping_service import FoodMappingService

    handler = GetFoodDetailsQueryHandler(
        food_data_service=StubFoodDataService(),
        cache_service=NoopFoodCacheService(),
        mapping_service=FoodMappingService(),
    )

    result = await handler.handle(GetFoodDetailsQuery(fdc_id=12345))

    assert result["fdc_id"] == 12345
    assert result["name"].lower().startswith("chicken")
    assert result["serving_size"] == 100.0
    assert result["serving_unit"] == "g"
    assert result["macros"]["protein"] == 31.0
    assert result["macros"]["carbs"] == 0.0
    assert result["macros"]["fat"] == 3.6
    assert result["calories"] == 165.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_manual_meal_command_handler_aggregates_items(monkeypatch):
    # Arrange
    from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand, ManualMealItem
    from src.app.handlers.command_handlers.create_manual_meal_command_handler import CreateManualMealCommandHandler
    from src.domain.services.food_mapping_service import FoodMappingService
    from src.domain.model.meal import MealStatus

    class StubMultiFoodService(StubFoodDataService):
        async def get_multiple_foods(self, fdc_ids: List[int]) -> List[Dict[str, Any]]:
            return [await self.get_food_details(fid) for fid in fdc_ids]

    handler = CreateManualMealCommandHandler(
        meal_repository=InMemoryMealRepository(),
        food_data_service=StubMultiFoodService(),
        mapping_service=FoodMappingService(),
    )

    items = [
        ManualMealItem(fdc_id=12345, quantity=150.0, unit="g"),  # 1.5x of 100g base
        ManualMealItem(fdc_id=12345, quantity=50.0, unit="g"),   # 0.5x of 100g base
    ]
    command = CreateManualMealCommand(
        user_id="550e8400-e29b-41d4-a716-446655440001",
        items=items,
        dish_name="Manual Chicken Mix",
    )

    # Act
    meal = await handler.handle(command)

    # Assert
    assert meal.meal_id is not None
    assert meal.status == MealStatus.READY
    assert meal.dish_name == "Manual Chicken Mix"
    assert meal.nutrition is not None

    # Total quantity = 200g => 2x 100g base => calories and macros doubled
    assert meal.nutrition.calories == pytest.approx(330.0)
    assert meal.nutrition.macros.protein == pytest.approx(62.0)
    assert meal.nutrition.macros.carbs == pytest.approx(0.0)
    assert meal.nutrition.macros.fat == pytest.approx(7.2)
