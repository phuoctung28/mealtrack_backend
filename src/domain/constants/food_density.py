"""Food density constants for ml→gram conversion."""

# Density in g/ml. Source: USDA, food science references.
# Used when user inputs volume (ml) for non-water liquids.
FOOD_DENSITY_MAP: dict[str, float] = {
    # Sweeteners
    "honey": 1.42,
    "maple syrup": 1.32,
    "corn syrup": 1.38,
    "molasses": 1.42,
    "agave": 1.35,
    # Oils & fats
    "oil": 0.92,
    "olive oil": 0.92,
    "coconut oil": 0.92,
    "vegetable oil": 0.92,
    "canola oil": 0.92,
    "sesame oil": 0.92,
    "butter": 0.91,
    "ghee": 0.90,
    # Dairy
    "milk": 1.03,
    "whole milk": 1.03,
    "skim milk": 1.03,
    "cream": 1.01,
    "heavy cream": 1.01,
    "yogurt": 1.05,
    "condensed milk": 1.28,
    # Sauces & condiments
    "soy sauce": 1.20,
    "fish sauce": 1.20,
    "oyster sauce": 1.30,
    "vinegar": 1.01,
    "ketchup": 1.15,
    "sriracha": 1.10,
    # Beverages
    "juice": 1.05,
    "coconut milk": 1.01,
}

# Default density for unknown liquids
DEFAULT_DENSITY = 1.0


def get_density(food_name: str) -> float:
    """Get density for food item. Matches keywords in food name."""
    name_lower = food_name.lower()
    # Try longest keys first to match "olive oil" before "oil"
    for key in sorted(FOOD_DENSITY_MAP, key=len, reverse=True):
        if key in name_lower:
            return FOOD_DENSITY_MAP[key]
    return DEFAULT_DENSITY
