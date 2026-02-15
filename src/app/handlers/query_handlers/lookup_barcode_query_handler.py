"""
LookupBarcodeQueryHandler - Handle barcode lookup with cascade: DB -> FatSecret -> OpenFoodFacts.
"""
import logging
from typing import Optional, Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.food.lookup_barcode_query import LookupBarcodeQuery
from src.infra.adapters.open_food_facts_service import OpenFoodFactsService
from src.infra.adapters.fat_secret_service import FatSecretService
from src.infra.repositories.barcode_product_repository import BarcodeProductRepository

logger = logging.getLogger(__name__)


@handles(LookupBarcodeQuery)
class LookupBarcodeQueryHandler(EventHandler[LookupBarcodeQuery, Optional[Dict[str, Any]]]):
    """Handler for looking up product by barcode with cascade logic."""

    def __init__(
        self,
        open_food_facts_service: OpenFoodFactsService,
        fat_secret_service: FatSecretService,
        barcode_product_repository: BarcodeProductRepository,
    ):
        self.off = open_food_facts_service
        self.fat_secret = fat_secret_service
        self.repo = barcode_product_repository

    async def handle(self, query: LookupBarcodeQuery) -> Optional[Dict[str, Any]]:
        """Look up product by barcode with cascade: DB -> FatSecret -> OpenFoodFacts."""

        # Step 1: Check local cache (DB)
        cached = self.repo.get_by_barcode(query.barcode)
        if cached:
            cached["source"] = "cache"
            return cached

        # Step 2: Try FatSecret
        fat_secret_result = self.fat_secret.get_product(query.barcode)
        if fat_secret_result:
            fat_secret_result["source"] = "fatsecret"
            self._cache_result(fat_secret_result)
            return fat_secret_result

        # Step 3: Try OpenFoodFacts
        off_result = self.off.get_product(query.barcode)
        if off_result:
            off_result["source"] = "openfoodfacts"
            self._cache_result(off_result)
            return off_result

        # Step 4: Not found
        return None

    def _cache_result(self, result: Dict[str, Any]) -> None:
        """Cache API result to local database (fail silently on error)."""
        try:
            self.repo.save(result)
        except Exception as e:
            logger.warning(f"Failed to cache barcode {result.get('barcode')}: {e}")
