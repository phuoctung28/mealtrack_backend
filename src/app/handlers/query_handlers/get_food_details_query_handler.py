"""
GetFoodDetailsQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
from typing import Any, Dict

from src.app.events.base import EventHandler, handles
from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery
from src.domain.services.food_mapping_service import FoodMappingService


@handles(GetFoodDetailsQuery)
class GetFoodDetailsQueryHandler(EventHandler[GetFoodDetailsQuery, Dict[str, Any]]):
    """Handler for getting food details by FDC ID."""

    def __init__(self, food_data_service, cache_service, mapping_service: FoodMappingService):
        self.food_data_service = food_data_service
        self.cache_service = cache_service
        self.mapping_service = mapping_service

    async def handle(self, event: GetFoodDetailsQuery) -> Dict[str, Any]:
        cached = await self.cache_service.get_cached_food(event.fdc_id)
        if cached is not None:
            return self.mapping_service.map_food_details(cached)

        raw = await self.food_data_service.get_food_details(event.fdc_id)
        await self.cache_service.cache_food(event.fdc_id, raw)
        return self.mapping_service.map_food_details(raw)
