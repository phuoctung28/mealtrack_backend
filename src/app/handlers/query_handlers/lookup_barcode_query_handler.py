"""
LookupBarcodeQueryHandler - Handle barcode lookup via OpenFoodFacts.
"""
from typing import Optional, Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery
from src.infra.adapters.open_food_facts_service import OpenFoodFactsService


@handles(LookupBarcodeQuery)
class LookupBarcodeQueryHandler(EventHandler[LookupBarcodeQuery, Optional[Dict[str, Any]]]):
    """Handler for looking up product by barcode."""

    def __init__(self, open_food_facts_service: OpenFoodFactsService):
        self.open_food_facts_service = open_food_facts_service

    async def handle(self, query: LookupBarcodeQuery) -> Optional[Dict[str, Any]]:
        """Look up product by barcode."""
        return self.open_food_facts_service.get_product(query.barcode)
