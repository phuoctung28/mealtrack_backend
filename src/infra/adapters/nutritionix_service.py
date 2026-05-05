"""
Nutritionix API HTTP client.
Provides product lookup by barcode (UPC) for packaged foods.
"""

import logging
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class NutritionixService:
    """HTTP client for Nutritionix Track API."""

    BASE_URL = "https://trackapi.nutritionix.com/v2"
    BARCODE_PATTERN = re.compile(r"^\d{8,14}$")

    def __init__(self, app_id: str, api_key: str):
        self._app_id = app_id
        self._api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create lazy async HTTP client with auth headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=5.0,
                headers={
                    "x-app-id": self._app_id,
                    "x-app-key": self._api_key,
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_product(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Fetch product by UPC barcode from Nutritionix.

        Args:
            barcode: Product barcode (EAN-8 to EAN-14 / UPC)

        Returns:
            Product dict with name, brand, nutrition per 100g, serving size, image URL.
            Returns None if product not found or API error.
        """
        if not self.BARCODE_PATTERN.match(barcode):
            return None

        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.BASE_URL}/search/item",
                params={"upc": barcode},
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()

            data = response.json()
            foods = data.get("foods")
            if not foods:
                return None

            return self._map_product(foods[0], barcode)
        except httpx.HTTPError as exc:
            logger.warning("Nutritionix HTTP error for barcode %s: %s", barcode, exc)
            return None
        except Exception as exc:
            logger.warning(
                "Nutritionix unexpected error for barcode %s: %s", barcode, exc
            )
            return None

    def _map_product(self, item: dict, barcode: str) -> Dict[str, Any]:
        """Map Nutritionix foods item to clean per-100g dict."""
        serving_weight = item.get("nf_serving_weight_grams") or 0.0
        use_per_100 = serving_weight <= 0

        def per_100(value: Optional[float]) -> Optional[float]:
            if value is None:
                return None
            if use_per_100:
                return value
            return round(value * 100.0 / serving_weight, 2)

        serving_qty = item.get("serving_qty")
        serving_unit = item.get("serving_unit")
        serving_size: Optional[str] = None
        if serving_qty is not None and serving_unit:
            serving_size = f"{serving_qty} {serving_unit}"

        return {
            "name": item.get("food_name"),
            "brand": item.get("brand_name"),
            "barcode": item.get("nix_item_id") or barcode,
            "protein_100g": per_100(item.get("nf_protein")),
            "carbs_100g": per_100(item.get("nf_total_carbohydrate")),
            "fat_100g": per_100(item.get("nf_total_fat")),
            "fiber_100g": per_100(item.get("nf_dietary_fiber")),
            "sugar_100g": per_100(item.get("nf_sugars")),
            "serving_size": serving_size,
            "image_url": (item.get("photo") or {}).get("thumb"),
        }


_nutritionix_service: Optional[NutritionixService] = None


def get_nutritionix_service() -> Optional[NutritionixService]:
    """Get singleton NutritionixService, or None if credentials not configured."""
    global _nutritionix_service
    if _nutritionix_service is not None:
        return _nutritionix_service

    from src.infra.config.settings import settings

    app_id = settings.NUTRITIONIX_APP_ID
    api_key = settings.NUTRITIONIX_API_KEY
    if not app_id or not api_key:
        return None

    _nutritionix_service = NutritionixService(app_id=app_id, api_key=api_key)
    return _nutritionix_service
