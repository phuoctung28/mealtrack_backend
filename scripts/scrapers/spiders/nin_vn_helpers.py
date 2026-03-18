"""Shared helpers for NIN VN spiders — column matching and cell parsing."""

import logging
import re

logger = logging.getLogger(__name__)

# Column header aliases for nutrient detection
# TODO: Verify actual column order from live site DevTools inspection
MACRO_COLUMNS: dict[str, list[str]] = {
    "protein": ["protein", "đạm", "protein (g)"],
    "carbs": ["carbohydrate", "glucid", "tinh bột", "carbs"],
    "fat": ["fat", "lipid", "chất béo", "béo"],
    "fiber": ["fiber", "chất xơ", "xơ"],
    "ca": ["ca", "calcium", "canxi"],
    "fe": ["fe", "iron", "sắt"],
    "vit_a": ["vit a", "vitamin a", "vit. a"],
    "vit_c": ["vit c", "vitamin c", "vit. c"],
}


def normalize_header(text: str) -> str:
    """Lowercase and strip a header cell."""
    return text.lower().strip()


def match_column(header: str, aliases: list[str]) -> bool:
    """Check if header matches any alias."""
    h = normalize_header(header)
    return any(alias in h for alias in aliases)


def safe_float(value: str) -> float:
    """Parse a cell value to float, returning 0.0 on failure."""
    cleaned = re.sub(r"[^\d.,]", "", value.replace(",", ".")).strip()
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def build_column_map(headers: list[str]) -> dict[str, int]:
    """Return {nutrient_key: col_index} for known headers."""
    col_map: dict[str, int] = {}
    for i, header in enumerate(headers):
        h_lower = normalize_header(header)
        # Name columns — TODO: adjust to actual site column names
        if any(kw in h_lower for kw in ["tên thực phẩm", "food name", "tên", "name"]):
            if h_lower in ("tên thực phẩm", "tên"):
                col_map["name_vi"] = i
            elif "name" in h_lower or "english" in h_lower:
                col_map.setdefault("name_en", i)
                col_map.setdefault("name_vi", i)
        # Macro + micro nutrients
        for nutrient, aliases in MACRO_COLUMNS.items():
            if match_column(header, aliases) and nutrient not in col_map:
                col_map[nutrient] = i

    # Fallbacks if name not resolved
    if "name_vi" not in col_map and len(headers) >= 1:
        col_map["name_vi"] = 0
    if "name_en" not in col_map and len(headers) >= 2:
        col_map["name_en"] = 1

    return col_map


def row_to_entry(
    cells: list[str],
    col_map: dict[str, int],
    category_raw: str,
    source: str = "nin_vn",
) -> dict | None:
    """Convert a table row to a FoodEntry-compatible dict."""
    try:
        name_vi = cells[col_map.get("name_vi", 0)] if col_map.get("name_vi", 0) < len(cells) else ""
        name_en = cells[col_map.get("name_en", 1)] if col_map.get("name_en", 1) < len(cells) else name_vi

        if not name_vi:
            return None

        def get_nutrient(key: str) -> float:
            idx = col_map.get(key)
            if idx is None or idx >= len(cells):
                return 0.0
            return safe_float(cells[idx])

        protein = get_nutrient("protein")
        carbs = get_nutrient("carbs")
        fat = get_nutrient("fat")

        # Skip rows with no macro data at all
        if protein == 0.0 and carbs == 0.0 and fat == 0.0:
            return None

        return {
            "name": name_en or name_vi,
            "name_vi": name_vi,
            "category": category_raw,
            "region": "VN",
            "source": source,
            "protein_100g": protein,
            "carbs_100g": carbs,
            "fat_100g": fat,
            "fiber_100g": get_nutrient("fiber"),
            "sugar_100g": 0.0,
            "density": 1.0,
            "extra_nutrients": {
                "ca_mg": get_nutrient("ca"),
                "fe_mg": get_nutrient("fe"),
                "vit_a_mcg": get_nutrient("vit_a"),
                "vit_c_mg": get_nutrient("vit_c"),
            },
            "barcode": None,
            "brand": None,
            "image_url": None,
        }
    except Exception as exc:
        logger.warning("Row parse error: %s | cells=%s", exc, cells)
        return None
