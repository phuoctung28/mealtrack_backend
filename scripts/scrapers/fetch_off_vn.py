"""
Fetch Vietnamese products from OpenFoodFacts API.

Usage:
    python fetch_off_vn.py
    python fetch_off_vn.py --output scripts/data/off_vn_products.json
    python fetch_off_vn.py --max-pages 5  # limit for testing
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Graceful import — common.schema may not exist yet during parallel Phase 1
try:
    from common.schema import save_entries  # type: ignore[import]
    HAS_COMMON_SCHEMA = True
except ImportError:
    HAS_COMMON_SCHEMA = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://world.openfoodfacts.org/api/v2/search"
USER_AGENT = "NutreeAI/1.0 (contact@nutree.ai)"
PAGE_SIZE = 100
RATE_LIMIT_SECONDS = 1.0

BASE_PARAMS: dict[str, Any] = {
    "countries_tags_contains": "en:vietnam",
    "page_size": PAGE_SIZE,
    "fields": (
        "code,product_name,product_name_vi,brands,categories,"
        "nutriments,image_url"
    ),
}


def fetch_page(session: requests.Session, page: int) -> list[dict]:
    """Fetch one page of products. Returns empty list when no more results."""
    params = {**BASE_PARAMS, "page": page}
    try:
        response = session.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        products: list[dict] = data.get("products", [])
        total_count = data.get("count", 0)
        logger.debug("Page %d: %d raw products (total=%d)", page, len(products), total_count)
        return products
    except requests.RequestException as exc:
        logger.error("Request failed (page=%d): %s", page, exc)
        return []
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error (page=%d): %s", page, exc)
        return []


def _safe_float(value: Any) -> float:
    """Coerce a nutriment value to float, returning 0.0 on failure."""
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def product_to_entry(product: dict) -> dict | None:
    """Map an OpenFoodFacts product dict to a FoodEntry-compatible dict.

    Returns None if the product is missing all macro nutrients.
    """
    nutriments: dict = product.get("nutriments") or {}

    protein = _safe_float(nutriments.get("proteins_100g"))
    carbs = _safe_float(nutriments.get("carbohydrates_100g"))
    fat = _safe_float(nutriments.get("fat_100g"))

    # Skip entries that are entirely devoid of macro data
    if protein == 0.0 and carbs == 0.0 and fat == 0.0:
        return None

    name_vi: str = (product.get("product_name_vi") or "").strip()
    name_en: str = (product.get("product_name") or "").strip()
    name = name_vi or name_en
    if not name:
        return None

    return {
        "name": name_en or name_vi,
        "name_vi": name_vi,
        "category": (product.get("categories") or "").split(",")[0].strip(),
        "region": "VN",
        "source": "openfoodfacts",
        "protein_100g": protein,
        "carbs_100g": carbs,
        "fat_100g": fat,
        "fiber_100g": _safe_float(nutriments.get("fiber_100g")),
        "sugar_100g": _safe_float(nutriments.get("sugars_100g")),
        "density": 1.0,
        "extra_nutrients": {
            "energy_kcal": _safe_float(nutriments.get("energy-kcal_100g")),
            "sodium_mg": _safe_float(nutriments.get("sodium_100g")) * 1000,
        },
        "barcode": product.get("code") or None,
        "brand": (product.get("brands") or "").split(",")[0].strip() or None,
        "image_url": product.get("image_url") or None,
    }


def fetch_all(max_pages: int | None = None) -> list[dict]:
    """Paginate through OpenFoodFacts VN products and return all valid entries."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    entries: list[dict] = []
    page = 1

    while True:
        if max_pages and page > max_pages:
            logger.info("Reached max_pages=%d limit", max_pages)
            break

        logger.info("Fetching page %d...", page)
        products = fetch_page(session, page)

        if not products:
            logger.info("Empty page %d — done paginating", page)
            break

        page_entries = 0
        for product in products:
            entry = product_to_entry(product)
            if entry:
                entries.append(entry)
                page_entries += 1

        total_on_page = len(products)
        logger.info(
            "Page %d: %d/%d products kept (total so far: %d)",
            page, page_entries, total_on_page, len(entries),
        )

        # Stop if fewer items than expected (last page can be slightly under)
        if total_on_page < PAGE_SIZE - 5:
            logger.info("Last page reached (got %d < %d)", total_on_page, PAGE_SIZE)
            break

        page += 1
        time.sleep(RATE_LIMIT_SECONDS)

    return entries


def save(entries: list[dict], output_path: Path) -> None:
    """Write entries to JSON, using common.schema.save_entries if available."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    logger.info("Saved %d entries to %s", len(entries), output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Vietnamese products from OpenFoodFacts")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../data/off_vn_products.json"),
        help="Output JSON file path (default: ../data/off_vn_products.json)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit number of pages fetched (useful for testing)",
    )
    args = parser.parse_args()

    logger.info("Starting OpenFoodFacts VN fetch (page_size=%d)", PAGE_SIZE)
    entries = fetch_all(max_pages=args.max_pages)

    if not entries:
        logger.error("No entries fetched — check network or API availability")
        sys.exit(1)

    save(entries, args.output)
    logger.info("Done. Total valid entries: %d", len(entries))


if __name__ == "__main__":
    main()
