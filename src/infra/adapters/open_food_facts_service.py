"""
OpenFoodFacts API HTTP client.
Provides product lookup by barcode for packaged foods.
"""
from typing import Dict, Any, Optional
import requests


class OpenFoodFactsService:
    """HTTP client for OpenFoodFacts API."""

    BASE_URL = "https://world.openfoodfacts.org/api/v2"

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def get_product(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Fetch product by barcode from OpenFoodFacts.

        Args:
            barcode: Product barcode (EAN-13, EAN-8, UPC-A, UPC-E)

        Returns:
            Product dict with name, brand, nutrition per 100g, serving size, image URL
            Returns None if product not found or API error.
        """
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/product/{barcode}.json",
                timeout=10,
                headers={"User-Agent": "Nutree/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != 1:
                return None

            product = data.get("product", {})
            if not product:
                return None

            return self._map_product(product)
        except requests.RequestException:
            return None

    def _map_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Map OpenFoodFacts response to clean dict."""
        nutriments = product.get("nutriments", {})

        # Get serving size from product
        serving_size = product.get("serving_size")
        if not serving_size:
            # Try to get from selected portion
            selected_portion = product.get("selected_portion")
            if selected_portion:
                serving_size = selected_portion.get("label")

        # Get image URL
        image_url = (
            product.get("image_front_url")
            or product.get("image_url")
            or product.get("image_front_small_url")
        )

        return {
            "name": product.get("product_name") or product.get("product_name_en"),
            "brand": product.get("brands"),
            "barcode": product.get("code"),
            "calories_100g": self._safe_float(nutriments.get("energy-kcal_100g")),
            "protein_100g": self._safe_float(nutriments.get("proteins_100g")),
            "carbs_100g": self._safe_float(nutriments.get("carbohydrates_100g")),
            "fat_100g": self._safe_float(nutriments.get("fat_100g")),
            "serving_size": serving_size,
            "image_url": image_url,
        }

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# Singleton instance
_open_food_facts_service: Optional[OpenFoodFactsService] = None


def get_open_food_facts_service() -> OpenFoodFactsService:
    """Get singleton instance of OpenFoodFactsService."""
    global _open_food_facts_service
    if _open_food_facts_service is None:
        _open_food_facts_service = OpenFoodFactsService()
    return _open_food_facts_service
