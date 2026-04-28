"""
Maps USDA FDC responses into internal simplified structures and domain-friendly dictionaries.
Keeps logic flat and readable.
"""

from typing import Dict, Any, List

USDA_NUTRIENT_MAPPING = {
    1008: "calories",  # Energy (cal)
    1003: "protein",  # Protein (g)
    1005: "carbs",  # Carbohydrate (g)
    1004: "fat",  # Total lipid (fat) (g)
}

# Fallback unit categories for custom/manual ingredients
FALLBACK_UNIT_CATEGORIES = {
    "solid": [
        {"unit": "g", "gram_weight": 1.0},
        {"unit": "kg", "gram_weight": 1000.0},
        {"unit": "oz", "gram_weight": 28.35},
        {"unit": "lb", "gram_weight": 453.6},
    ],
    "liquid": [
        {"unit": "ml", "gram_weight": 1.0},
        {"unit": "l", "gram_weight": 1000.0},
        {"unit": "cup", "gram_weight": 240.0},
        {"unit": "tbsp", "gram_weight": 15.0},
        {"unit": "tsp", "gram_weight": 5.0},
    ],
    "countable": [
        {"unit": "piece", "gram_weight": 1.0},
        {"unit": "g", "gram_weight": 1.0},
        {"unit": "oz", "gram_weight": 28.35},
    ],
    "powder": [
        {"unit": "g", "gram_weight": 1.0},
        {"unit": "tbsp", "gram_weight": 8.0},
        {"unit": "tsp", "gram_weight": 3.0},
        {"unit": "cup", "gram_weight": 120.0},
    ],
}

DEFAULT_ALLOWED_UNITS = [{"unit": "g", "gram_weight": 1.0, "description": "1 g"}]


from src.domain.ports.food_mapping_service_port import FoodMappingServicePort


class FoodMappingService(FoodMappingServicePort):
    def map_search_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # Handle FatSecret results with embedded nutrition
        if item.get("source") == "fatsecret":
            return {
                "fdc_id": None,  # FatSecret doesn't use FDC IDs
                "food_id": item.get("food_id"),
                "name": item.get("description"),
                "brand": item.get("brand"),
                "data_type": "fatsecret",
                "serving_size": item.get("serving_description"),
                "serving_unit": "g",
                "calories": item.get("calories_100g"),
                "nutrients": {
                    "protein": item.get("protein_100g"),
                    "fat": item.get("fat_100g"),
                    "carbs": item.get("carbs_100g"),
                },
                "source": "fatsecret",
                "allowed_units": item.get("allowed_units") or DEFAULT_ALLOWED_UNITS,
                # Include custom nutrition for manual meal creation
                "custom_nutrition": (
                    {
                        "calories_per_100g": item.get("calories_100g") or 0,
                        "protein_per_100g": item.get("protein_100g") or 0,
                        "carbs_per_100g": item.get("carbs_100g") or 0,
                        "fat_per_100g": item.get("fat_100g") or 0,
                    }
                    if item.get("calories_100g")
                    else None
                ),
            }

        # USDA results
        nutrients = self._extract_macros(item.get("foodNutrients") or [])

        result = {
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
            "allowed_units": (
                self._parse_usda_portions(item.get("foodPortions"))
                if item.get("foodPortions")
                else DEFAULT_ALLOWED_UNITS
            ),
        }
        if "source" in item:
            result["source"] = item["source"]
        return result

    def _parse_usda_portions(
        self, portions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse USDA foodPortions into allowed_units format."""
        if not portions:
            return DEFAULT_ALLOWED_UNITS

        units = []
        for portion in portions:
            measure = portion.get("measureUnit", {})
            unit_name = measure.get("name") or measure.get("abbreviation") or "portion"
            gram_weight = portion.get("gramWeight")
            description = portion.get("portionDescription", "")

            if gram_weight and float(gram_weight) > 0:
                units.append(
                    {
                        "unit": unit_name,
                        "gram_weight": float(gram_weight),
                        "description": description,
                    }
                )

        if not units:
            return DEFAULT_ALLOWED_UNITS

        # Ensure "g" is always present
        if not any(u["unit"].lower() == "g" for u in units):
            units.insert(0, {"unit": "g", "gram_weight": 1.0, "description": "1 g"})

        return units

    def _extract_macros(self, nutrients: List[Dict[str, Any]]) -> Dict[str, float]:
        values: Dict[str, float] = {
            "calories": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
        }
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
            "allowed_units": (
                self._parse_usda_portions(details.get("foodPortions"))
                if details.get("foodPortions")
                else DEFAULT_ALLOWED_UNITS
            ),
        }
