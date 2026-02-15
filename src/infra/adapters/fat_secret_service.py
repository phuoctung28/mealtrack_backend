"""
FatSecret API HTTP client.
Provides product lookup by barcode and food search.
"""
from typing import Dict, Any, Optional, List
import logging

import fatsecret

from src.infra.config.settings import settings

logger = logging.getLogger(__name__)


class FatSecretService:
    """HTTP client for FatSecret API."""

    def __init__(self, consumer_key: str, consumer_secret: str):
        self.client = fatsecret.Fatsecret(consumer_key, consumer_secret)

    def get_product(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Fetch product by barcode from FatSecret."""
        try:
            normalized_barcode = barcode.zfill(13)
            search_results = self.client.food_find_id_for_barcode(
                barcode=normalized_barcode
            )
            if not search_results:
                return None
            food_id = search_results.get("food_id")
            if not food_id:
                return None
            food_details = self.client.food_get(food_id)
            if not food_details:
                return None
            return self._map_product(food_details, normalized_barcode)
        except Exception as e:
            logger.warning(f"FatSecret API error for barcode {barcode}: {e}")
            return None

    def search_foods(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search foods by query string."""
        try:
            results = self.client.foods_search(
                query, max_results=max_results, page_number=1
            )
            if not results:
                return []
            foods = results.get("foods", {}).get("food", [])
            if not foods:
                return []
            if isinstance(foods, dict):
                foods = [foods]
            return [self._map_search_result(food) for food in foods]
        except Exception as e:
            logger.warning(f"FatSecret search error for query '{query}': {e}")
            return []

    def _map_product(self, food: Dict[str, Any], barcode: str) -> Dict[str, Any]:
        """Map FatSecret response to clean dict."""
        servings = food.get("servings", {}).get("serving", [])
        serving = None
        if isinstance(servings, list) and servings:
            serving = servings[0]
        elif isinstance(servings, dict):
            serving = servings
        if not isinstance(serving, dict):
            return {
                "name": food.get("food_name", ""),
                "brand": food.get("brand_name"),
                "barcode": barcode,
                "calories_100g": None,
                "protein_100g": None,
                "carbs_100g": None,
                "fat_100g": None,
                "serving_size": None,
                "image_url": None,
            }
        serving_quantity = self._safe_float(serving.get("number_of_units")) or 1
        return {
            "name": food.get("food_name", ""),
            "brand": food.get("brand_name"),
            "barcode": barcode,
            "calories_100g": self._safe_float(serving.get("calories")) / serving_quantity * 100 if serving.get("calories") else None,
            "protein_100g": self._safe_float(serving.get("protein")) / serving_quantity * 100 if serving.get("protein") else None,
            "carbs_100g": self._safe_float(serving.get("carbohydrate")) / serving_quantity * 100 if serving.get("carbohydrate") else None,
            "fat_100g": self._safe_float(serving.get("fat")) / serving_quantity * 100 if serving.get("fat") else None,
            "serving_size": serving.get("serving_description"),
            "image_url": food.get("food_url"),
        }

    def _map_search_result(self, food: Dict[str, Any]) -> Dict[str, Any]:
        """Map FatSecret search result to clean dict."""
        return {
            "description": food.get("food_name", ""),
            "brand": food.get("brand_name"),
            "food_description": food.get("food_description", ""),
            "source": "fatsecret",
        }

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


_fat_secret_service: Optional[FatSecretService] = None


def get_fat_secret_service() -> FatSecretService:
    """Get singleton instance of FatSecretService."""
    global _fat_secret_service
    if _fat_secret_service is None:
        _fat_secret_service = FatSecretService(
            consumer_key=settings.FATSECRET_CONSUMER_KEY,
            consumer_secret=settings.FATSECRET_CONSUMER_SECRET,
        )
    return _fat_secret_service
