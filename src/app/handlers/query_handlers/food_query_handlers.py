"""
Query handlers for food database feature.
"""
from typing import Any, Dict

from src.app.events.base import EventHandler, handles
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.app.queries.food.get_food_details_query import GetFoodDetailsQuery
from src.domain.services.food_mapping_service import FoodMappingService


class SearchFoodsQueryHandler(EventHandler[SearchFoodsQuery, Dict[str, Any]]):
    def __init__(self, food_data_service, cache_service, mapping_service: FoodMappingService):
        self.food_data_service = food_data_service
        self.cache_service = cache_service
        self.mapping_service = mapping_service

    async def handle(self, event: SearchFoodsQuery) -> Dict[str, Any]:
        if not event.query or not event.query.strip():
            return {"results": [], "query": event.query, "total": 0}

        cached = await self.cache_service.get_cached_search(event.query)
        if cached is not None:
            mapped = [self.mapping_service.map_search_item(i) for i in cached]
            return {"results": mapped, "query": event.query, "total": len(mapped)}

        raw = await self.food_data_service.search_foods(event.query, event.limit)
        await self.cache_service.cache_search(event.query, raw)
        mapped = [self.mapping_service.map_search_item(i) for i in raw]
        return {"results": mapped, "query": event.query, "total": len(mapped)}


class GetFoodDetailsQueryHandler(EventHandler[GetFoodDetailsQuery, Dict[str, Any]]):
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
