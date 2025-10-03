"""
SearchFoodsQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
from typing import Any, Dict, List

from src.app.events.base import EventHandler, handles
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.domain.services.food_mapping_service import FoodMappingService


@handles(SearchFoodsQuery)
class SearchFoodsQueryHandler(EventHandler[SearchFoodsQuery, Dict[str, Any]]):
    """Handler for searching foods in the database."""

    def __init__(self, food_data_service, cache_service, mapping_service: FoodMappingService):
        self.food_data_service = food_data_service
        self.cache_service = cache_service
        self.mapping_service = mapping_service

    async def handle(self, event: SearchFoodsQuery) -> Dict[str, Any]:
        if not event.query or not event.query.strip():
            return {"results": [], "query": event.query, "total": 0}

        cached = await self.cache_service.get_cached_search(event.query)
        if cached is not None:
            # Process cached results as well
            processed_cached = self._process_search_results(cached)
            mapped = [self.mapping_service.map_search_item(i) for i in processed_cached]
            return {"results": mapped, "query": event.query, "total": len(mapped)}

        raw = await self.food_data_service.search_foods(event.query, event.limit)

        # Process results: deduplicate exact matches and capitalize names
        processed_raw = self._process_search_results(raw)

        await self.cache_service.cache_search(event.query, processed_raw)
        mapped = [self.mapping_service.map_search_item(i) for i in processed_raw]
        return {"results": mapped, "query": event.query, "total": len(mapped)}

    def _process_search_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process search results to:
        1. Deduplicate exact matches (keep only first occurrence)
        2. Capitalize food names properly
        """
        if not raw_results:
            return raw_results

        seen_names = set()
        processed_results = []

        for item in raw_results:
            # Get the original name
            original_name = item.get("description", "")

            # Capitalize the name properly
            capitalized_name = self._capitalize_food_name(original_name)

            # Check for exact duplicates (case-insensitive)
            name_key = capitalized_name.lower().strip()

            if name_key not in seen_names:
                # First occurrence of this name, keep it
                seen_names.add(name_key)

                # Create a copy and update the name
                processed_item = item.copy()
                processed_item["description"] = capitalized_name
                processed_results.append(processed_item)

        return processed_results

    def _capitalize_food_name(self, name: str) -> str:
        """
        Properly capitalize food names.
        Examples:
        - "CHICKEN BREAST" -> "Chicken Breast"
        - "chicken breast" -> "Chicken Breast"
        - "CHICKEN BREAST, BONELESS" -> "Chicken Breast, Boneless"
        """
        if not name:
            return name

        # Split by common separators and capitalize each part
        parts = []
        for part in name.split(','):
            # Capitalize each word in the part
            words = []
            for word in part.strip().split():
                # Handle special cases for common food terms
                word_lower = word.lower()
                if word_lower in ['and', 'or', 'with', 'in', 'on', 'of', 'the', 'a', 'an']:
                    # Keep articles and prepositions lowercase unless they're the first word
                    words.append(word_lower if words else word.capitalize())
                else:
                    words.append(word.capitalize())

            if words:
                parts.append(' '.join(words))

        return ', '.join(parts)
