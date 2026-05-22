"""Hydration drink catalog — static data for v1.

All drink metadata lives here so the application and API layers
can resolve drink details without hitting the database.
"""

from typing import Dict, List, Optional

from src.domain.model.hydration import Drink

# ---------------------------------------------------------------------------
# Static catalog data
# ---------------------------------------------------------------------------

_DRINKS: List[Drink] = [
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
        category="hydration",
    ),
    Drink(
        id="sparkling",
        name="Sparkling water",
        sub=None,
        emoji="🫧",
        default_ml=250,
        kcal_per_100ml=0.0,
        sugar_per_100ml=0.0,
        hydration_weight=1.0,
        brand_color="#60A5FA",
        category="hydration",
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
        category="hydration",
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
        category="hydration",
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
        category="hydration",
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
        category="caloric",
    ),
    Drink(
        id="coke",
        name="Coca-Cola",
        sub="Regular",
        emoji="🥤",
        default_ml=330,
        kcal_per_100ml=42.1,
        sugar_per_100ml=10.6,
        hydration_weight=0.80,
        brand_color="#B91C1C",
        category="caloric",
    ),
    Drink(
        id="coke-zero",
        name="Coke Zero",
        sub="Diet",
        emoji="🥤",
        default_ml=330,
        kcal_per_100ml=0.0,
        sugar_per_100ml=0.0,
        hydration_weight=1.0,
        brand_color="#1F2937",
        category="caloric",
    ),
    Drink(
        id="oj",
        name="Orange juice",
        sub="Fresh",
        emoji="🍊",
        default_ml=250,
        kcal_per_100ml=44.0,
        sugar_per_100ml=8.8,
        hydration_weight=0.95,
        brand_color="#F97316",
        category="caloric",
    ),
    Drink(
        id="iced-latte",
        name="Iced latte",
        sub="Café · milk",
        emoji="☕",
        default_ml=350,
        kcal_per_100ml=37.1,
        sugar_per_100ml=3.4,
        hydration_weight=0.85,
        brand_color="#92400E",
        category="caloric",
    ),
    Drink(
        id="smoothie",
        name="Smoothie",
        sub="Açaí blend",
        emoji="🥤",
        default_ml=400,
        kcal_per_100ml=62.5,
        sugar_per_100ml=7.5,
        hydration_weight=0.90,
        brand_color="#7C3AED",
        category="caloric",
    ),
    Drink(
        id="energy",
        name="Energy drink",
        sub="Red Bull",
        emoji="⚡",
        default_ml=250,
        kcal_per_100ml=44.0,
        sugar_per_100ml=10.8,
        hydration_weight=0.85,
        brand_color="#0EA5E9",
        category="caloric",
    ),
    Drink(
        id="beer",
        name="Beer",
        sub="Lager · 5%",
        emoji="🍺",
        default_ml=330,
        kcal_per_100ml=45.5,
        sugar_per_100ml=0.0,
        hydration_weight=0.60,
        brand_color="#CA8A04",
        category="caloric",
    ),
]

# Module-level constant — dict keyed by drink id for O(1) lookup.
DRINK_CATALOG: Dict[str, Drink] = {drink.id: drink for drink in _DRINKS}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_all() -> List[Drink]:
    """Return all drinks in catalog order."""
    return list(_DRINKS)


def find_by_id(drink_id: str) -> Optional[Drink]:
    """Return a Drink by its id, or None if not found."""
    return DRINK_CATALOG.get(drink_id)
