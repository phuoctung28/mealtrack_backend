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
        id="sparkling",
        name="Sparkling",
        sub="Carbonated",
        emoji="🫧",
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
        id="coke-zero",
        name="Coke Zero",
        sub="No sugar",
        emoji="🥤",
        default_ml=330,
        kcal_per_100ml=0.0,
        sugar_per_100ml=0.0,
        hydration_weight=1.0,
        brand_color="#1F2937",
        category=DrinkCategory.HYDRATION,
    ),
    # -----------------------------------------------------------------------
    # Caloric drinks
    # -----------------------------------------------------------------------
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
        category=DrinkCategory.CALORIC,
    ),
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
        category=DrinkCategory.CALORIC,
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
        category=DrinkCategory.CALORIC,
    ),
    Drink(
        id="iced-latte",
        name="Iced latte",
        sub="Cold brew",
        emoji="🧊",
        default_ml=350,
        kcal_per_100ml=37.1,
        sugar_per_100ml=2.9,
        hydration_weight=0.85,
        brand_color="#F59E0B",
        category=DrinkCategory.CALORIC,
    ),
    Drink(
        id="beer",
        name="Beer",
        sub="Lager",
        emoji="🍺",
        default_ml=330,
        kcal_per_100ml=45.5,
        sugar_per_100ml=1.2,
        hydration_weight=0.60,
        brand_color="#D97706",
        category=DrinkCategory.CALORIC,
    ),
]

# Module-level constant — dict keyed by drink id for O(1) lookup.
DRINK_CATALOG: dict[str, Drink] = {drink.id: drink for drink in _DRINKS}

_DRINK_TRANSLATIONS: dict[str, dict[str, dict[str, str | None]]] = {
    "vi": {
        "water": {"name": "Nước lọc", "sub": None},
        "sparkling": {"name": "Nước soda", "sub": "Có ga"},
        "tea": {"name": "Trà", "sub": None},
        "coffee": {"name": "Cà phê", "sub": None},
        "electrolyte": {"name": "Nước điện giải", "sub": "Nước thể thao"},
        "milk-tea": {"name": "Trà sữa", "sub": "Trân châu"},
        "coke": {"name": "Nước ngọt", "sub": "Có ga"},
        "coke-zero": {"name": "Coke Zero", "sub": "Không đường"},
        "oj": {"name": "Nước ép", "sub": "Ép tươi"},
        "smoothie": {"name": "Sinh tố", "sub": "Hỗn hợp Açaí"},
        "energy": {"name": "Nước tăng lực", "sub": "Red Bull"},
        "iced-latte": {"name": "Latte đá", "sub": "Cold brew"},
        "beer": {"name": "Bia", "sub": "Lager"},
    }
}

_DRINK_IDS_BY_ENGLISH_NAME: dict[str, str] = {
    drink.name.lower(): drink.id for drink in _DRINKS
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_all() -> list[Drink]:
    """Return all drinks in catalog order."""
    return list(_DRINKS)


def find_by_id(drink_id: str) -> Drink | None:
    """Return a Drink by its id, or None if not found."""
    return DRINK_CATALOG.get(drink_id)


def localized_name(drink: Drink, language: str = "en") -> str:
    """Return a localized drink name, falling back to the catalog name."""
    return (
        _DRINK_TRANSLATIONS.get(language, {}).get(drink.id, {}).get("name")
        or drink.name
    )


def localized_sub(drink: Drink, language: str = "en") -> str | None:
    """Return a localized drink subtitle, falling back to the catalog subtitle."""
    if language not in _DRINK_TRANSLATIONS:
        return drink.sub
    return _DRINK_TRANSLATIONS[language].get(drink.id, {}).get("sub", drink.sub)


def localized_name_for_catalog_name(
    name: str | None, language: str = "en"
) -> str | None:
    """Localize a stored canonical catalog name."""
    if not name:
        return name
    drink_id = _DRINK_IDS_BY_ENGLISH_NAME.get(name.lower())
    drink = DRINK_CATALOG.get(drink_id) if drink_id else None
    return localized_name(drink, language) if drink else name
