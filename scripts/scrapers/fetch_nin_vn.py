"""
Fetch Vietnamese food + dish nutrition data from viendinhduong.vn API.

APIs discovered:
  Foods:  /api/fe/foodNatunal/getPageFoodData  (853 items, 55+ nutrients)
  Dishes: /api/fe/tool/getPageFoodData          (1249 items, 14 nutrients)

Usage:
  python fetch_nin_vn.py [--output-foods FILE] [--output-dishes FILE] [--foods-only] [--dishes-only]
"""

import argparse
import json
import logging
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://viendinhduong.vn"
FOODS_API = f"{BASE_URL}/api/fe/foodNatunal/getPageFoodData"
DISHES_API = f"{BASE_URL}/api/fe/tool/getPageFoodData"
HEADERS = {"User-Agent": "NutreeAI/1.0 (food-database-enrichment)"}
PAGE_SIZE = 15  # API ignores limit param, always returns 15
RATE_LIMIT = 1.0  # seconds between requests

# Nutrient name mapping → our schema field names
NUTRIENT_MAP = {
    "protein": "protein_100g",
    "total lipid (fat)": "fat_100g",
    "lipid": "fat_100g",
    "carbohydrate by difference": "carbs_100g",
    "glucid": "carbs_100g",
    "dietary fiber": "fiber_100g",
    "sugars, total": "sugar_100g",
}

EXTRA_NUTRIENT_MAP = {
    "ca": "ca_mg",
    "fe": "fe_mg",
    "vit a-rae": "vit_a_mcg",
    "vitamin a": "vit_a_mcg",
    "retinol": "retinol_mcg",
    "vit c": "vit_c_mg",
    "na": "na_mg",
    "k": "k_mg",
    "zn": "zn_mg",
    "mg": "mg_mg",
    "p": "p_mg",
    "vit d (d2 +d3)": "vit_d_mcg",
    "vit e": "vit_e_mg",
    "thiamin": "thiamin_mg",
    "riboflavin": "riboflavin_mg",
    "niacin": "niacin_mg",
    "vit b6": "vit_b6_mg",
    "folate, total": "folate_mcg",
}


def _safe_float(val) -> float:
    """Convert API value to float, handling empty strings and None."""
    if val is None or val == "":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _parse_food_item(item: dict) -> dict:
    """Convert food API item to FoodEntry dict."""
    entry = {
        "name": item.get("name_en", "") or item.get("name_vi", ""),
        "name_vi": item.get("name_vi", ""),
        "category": item.get("categoryEn", "") or item.get("category", ""),
        "region": "VN",
        "source": "nin_vn",
        "protein_100g": 0.0,
        "carbs_100g": 0.0,
        "fat_100g": 0.0,
        "fiber_100g": 0.0,
        "sugar_100g": 0.0,
        "density": 1.0,
        "extra_nutrients": {},
        "barcode": None,
        "brand": None,
        "image_url": None,
    }

    for n in item.get("nutrition", []):
        name_lower = (n.get("name_en") or n.get("name", "")).lower().strip()
        val = _safe_float(n.get("value"))
        if val == 0.0:
            continue

        # Check macro mapping first
        if name_lower in NUTRIENT_MAP:
            entry[NUTRIENT_MAP[name_lower]] = val
        # Then extra nutrients
        elif name_lower in EXTRA_NUTRIENT_MAP:
            entry["extra_nutrients"][EXTRA_NUTRIENT_MAP[name_lower]] = val

    return entry


def _parse_dish_item(item: dict) -> dict:
    """Convert dish API item to FoodEntry dict."""
    entry = {
        "name": item.get("name_en", "") or item.get("name_vi", ""),
        "name_vi": item.get("name_vi", ""),
        "category": item.get("category_name_en", "") or item.get("category_name", ""),
        "region": "VN",
        "source": "nin_vn",
        "protein_100g": 0.0,
        "carbs_100g": 0.0,
        "fat_100g": 0.0,
        "fiber_100g": 0.0,
        "sugar_100g": 0.0,
        "density": 1.0,
        "extra_nutrients": {},
        "barcode": None,
        "brand": None,
        "image_url": None,
    }

    for n in item.get("nutritional_components", []):
        name_lower = (n.get("nameEn") or n.get("name", "")).lower().strip()
        val = _safe_float(n.get("amount"))
        if val == 0.0:
            continue

        if name_lower in NUTRIENT_MAP:
            entry[NUTRIENT_MAP[name_lower]] = val
        elif name_lower in EXTRA_NUTRIENT_MAP:
            entry["extra_nutrients"][EXTRA_NUTRIENT_MAP[name_lower]] = val

    return entry


def _fetch_paginated(api_url: str, parser, label: str) -> list[dict]:
    """Fetch all pages from a paginated API endpoint."""
    entries: list[dict] = []
    page = 1

    while True:
        params = {"page": page, "limit": PAGE_SIZE, "foodGroupId": "", "energyType": 0, "lang": "en"}
        try:
            r = requests.get(api_url, params=params, timeout=30, headers=HEADERS)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.error("Failed to fetch %s page %d: %s", label, page, e)
            break

        items = data.get("data", [])
        if not items:
            break

        total = data.get("total", "?")
        for item in items:
            entry = parser(item)
            if entry.get("name_vi"):
                entries.append(entry)

        logger.info("%s: page %d/%s — %d items (total so far: %d)",
                    label, page, data.get("last_page", "?"), len(items), len(entries))

        # Use actual per_page from response (API ignores our limit param)
        actual_page_size = data.get("per_page", PAGE_SIZE)
        if len(items) < actual_page_size:
            break
        page += 1
        time.sleep(RATE_LIMIT)

    logger.info("%s: fetched %d entries (API total: %s)", label, len(entries), total)
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch VN food/dish data from viendinhduong.vn API")
    parser.add_argument("--output-foods", default="scripts/data/nin_vn_foods.json")
    parser.add_argument("--output-dishes", default="scripts/data/nin_vn_dishes.json")
    parser.add_argument("--foods-only", action="store_true")
    parser.add_argument("--dishes-only", action="store_true")
    args = parser.parse_args()

    if not args.dishes_only:
        foods = _fetch_paginated(FOODS_API, _parse_food_item, "Foods")
        Path(args.output_foods).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_foods, "w", encoding="utf-8") as f:
            json.dump(foods, f, ensure_ascii=False, indent=2)
        logger.info("Saved %d foods to %s", len(foods), args.output_foods)

    if not args.foods_only:
        dishes = _fetch_paginated(DISHES_API, _parse_dish_item, "Dishes")
        Path(args.output_dishes).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_dishes, "w", encoding="utf-8") as f:
            json.dump(dishes, f, ensure_ascii=False, indent=2)
        logger.info("Saved %d dishes to %s", len(dishes), args.output_dishes)


if __name__ == "__main__":
    main()
