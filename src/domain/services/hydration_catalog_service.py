"""Hydration drink catalog — static data for v1.

All drink metadata lives here so the application and API layers
can resolve drink details without hitting the database.
"""

from src.domain.model.hydration import Drink, DrinkCategory

# ---------------------------------------------------------------------------
# Static catalog data
# ---------------------------------------------------------------------------

_DRINKS: list[Drink] = [
    # -----------------------------------------------------------------------
    # Zero-calorie / hydration drinks
    # -----------------------------------------------------------------------
    Drink(
        id="water",
        name="Water",
        sub=None,
        emoji="💧",
        default_ml=250,
        kcal_per_100ml=0.0,
        sugar_per_100ml=0.0,
        hydration_weight=1.0,
        brand_color="#3B82F6",
        category=DrinkCategory.HYDRATION,
    ),
    Drink(
        id="tea",
        name="Tea",
        sub=None,
        emoji="🍵",
        default_ml=250,
        kcal_per_100ml=0.0,
        sugar_per_100ml=0.0,
        hydration_weight=0.90,
        brand_color="#78716C",
        category=DrinkCategory.HYDRATION,
    ),
    Drink(
        id="coffee",
        name="Coffee",
        sub=None,
        emoji="☕",
        default_ml=250,
        kcal_per_100ml=0.0,
        sugar_per_100ml=0.0,
        hydration_weight=0.80,
        brand_color="#92400E",
        category=DrinkCategory.HYDRATION,
    ),
    Drink(
        id="electrolyte",
        name="Electrolyte",
        sub="Sports drink",
        emoji="⚡",
        default_ml=500,
        kcal_per_100ml=2.0,
        sugar_per_100ml=0.8,
        hydration_weight=0.95,
        brand_color="#22C55E",
        category=DrinkCategory.HYDRATION,
    ),
    # -----------------------------------------------------------------------
    # Caloric drinks
    # -----------------------------------------------------------------------
    Drink(
        id="milk-tea",
        name="Milk tea",
        sub="Boba",
        emoji="🧋",
        default_ml=500,
        kcal_per_100ml=76.0,
        sugar_per_100ml=9.0,
        hydration_weight=0.70,
        brand_color="#A87C5F",
        category=DrinkCategory.CALORIC,
    ),
    Drink(
        id="coke",
        name="Soda",
        sub="Soft drink",
        emoji="🥤",
        default_ml=330,
        kcal_per_100ml=42.1,
        sugar_per_100ml=10.6,
        hydration_weight=0.80,
        brand_color="#B91C1C",
        category=DrinkCategory.CALORIC,
    ),
    Drink(
        id="oj",
        name="Fruit juice",
        sub="Fresh pressed",
        emoji="🧃",
        default_ml=250,
        kcal_per_100ml=44.0,
        sugar_per_100ml=8.8,
        hydration_weight=0.95,
        brand_color="#F97316",
        category=DrinkCategory.CALORIC,
    ),
]

# Module-level constant — dict keyed by drink id for O(1) lookup.
DRINK_CATALOG: dict[str, Drink] = {drink.id: drink for drink in _DRINKS}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_all() -> list[Drink]:
    """Return all drinks in catalog order."""
    return list(_DRINKS)


def find_by_id(drink_id: str) -> Drink | None:
    """Return a Drink by its id, or None if not found."""
    return DRINK_CATALOG.get(drink_id)
