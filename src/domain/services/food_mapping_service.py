"""
Maps USDA FDC responses into internal simplified structures and domain-friendly dictionaries.
Keeps logic flat and readable.
"""
from typing import Dict, Any, List, Optional

USDA_NUTRIENT_MAPPING = {
    1008: "calories",  # Energy (kcal)
    1003: "protein",   # Protein (g)
    1005: "carbs",     # Carbohydrate (g)
    1004: "fat",       # Total lipid (fat) (g)
}


from src.domain.ports.food_mapping_service_port import FoodMappingServicePort


class FoodMappingService(FoodMappingServicePort):
    def map_search_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # Extract nutrients from search results
        nutrients = self._extract_macros(item.get("foodNutrients") or [])
        
        return {
            "fdc_id": item.get("fdcId"),
            "name": item.get("description"),
            "brand": item.get("brandOwner"),
            "data_type": item.get("dataType"),
            "published_date": item.get("publishedDate"),
            "serving_size": item.get("servingSize"),
            "serving_unit": item.get("servingSizeUnit"),
            "calories": nutrients.get("calories"),
            "nutrients": {
                "protein": nutrients.get("protein"),
                "fat": nutrients.get("fat"),
                "carbs": nutrients.get("carbs"),
            },
        }

    def _extract_macros(self, nutrients: List[Dict[str, Any]]) -> Dict[str, float]:
        values: Dict[str, float] = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for entry in nutrients or []:
            # Handle both search results format and details format
            if "nutrient" in entry:
                # Details format: nested structure
                nutrient = entry.get("nutrient") or {}
                nutrient_id = nutrient.get("id")
                amount = float(entry.get("amount") or 0.0)
            else:
                # Search results format: flat structure
                nutrient_id = entry.get("nutrientId")
                amount = float(entry.get("value") or 0.0)
            
            key = USDA_NUTRIENT_MAPPING.get(nutrient_id)
            if key:
                values[key] = amount
        return values

    def map_food_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        macros = self._extract_macros(details.get("foodNutrients") or [])
        return {
            "fdc_id": details.get("fdcId"),
            "name": details.get("description"),
            "brand": details.get("brandOwner"),
            "serving_size": details.get("servingSize"),
            "serving_unit": details.get("servingSizeUnit"),
            "calories": macros.get("calories"),
            "macros": {
                "protein": macros.get("protein"),
                "carbs": macros.get("carbs"),
                "fat": macros.get("fat"),
            },
            "portions": details.get("foodPortions") or [],
        }
