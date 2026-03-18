"""
Parse Vietnamese Food Composition Table PDF → standardized JSON.

Usage:
    python parse-vn-fct-pdf.py <path-to-pdf> [--output scripts/data/vn_fct_foods.json]

Extracts ~613 food items organized by food group chapters.
All nutrient values are per 100g edible portion.
"""
import argparse
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

# Resolve import paths relative to this script's directory
sys.path.insert(0, str(Path(__file__).parent))

from common.normalize import normalize_category, normalize_vi_name, validate_macros
from common.schema import FoodEntry, save_entries
from pdf_row_extractor import (
    extract_macros_and_micros,
    extract_names,
    is_footnote_row,
    is_food_group_header,
    is_header_row,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _build_entry(
    cells: list[Optional[str]],
    food_group: str,
) -> Optional[FoodEntry]:
    """Convert a PDF table row to a FoodEntry. Returns None if row is invalid."""
    name_vi, name_en = extract_names(cells)
    if not name_vi:
        return None

    nutrients = extract_macros_and_micros(cells)
    extra: dict = {}
    for key in ("calcium_mg", "iron_mg", "vitamin_a_mcg", "vitamin_c_mg"):
        val = nutrients.pop(key, 0.0)
        if val > 0.0:
            extra[key] = val

    entry = FoodEntry(
        name=normalize_vi_name(name_en) if name_en else normalize_vi_name(name_vi),
        name_vi=normalize_vi_name(name_vi),
        category=normalize_category(food_group),
        source="vn_fct_pdf",
        region="VN",
        protein_100g=nutrients["protein_100g"],
        carbs_100g=nutrients["carbs_100g"],
        fat_100g=nutrients["fat_100g"],
        fiber_100g=nutrients["fiber_100g"],
        extra_nutrients=extra,
    )

    warnings = validate_macros(entry)
    for w in warnings:
        logger.warning("[%s] %s", entry.name_vi, w)

    return entry


def _process_table(
    table: list[list[Optional[str]]],
    current_group: str,
) -> tuple[list[FoodEntry], str]:
    """
    Process a single pdfplumber table.
    Returns (entries_found, updated_food_group).
    """
    entries: list[FoodEntry] = []

    for row in table:
        if not row or all(c is None or not str(c).strip() for c in row):
            continue

        cells = [str(c).strip() if c is not None else "" for c in row]

        # Check for food group header (single-cell spanning rows)
        group_name = is_food_group_header(cells)
        if group_name:
            current_group = group_name
            logger.info("Food group: %s", current_group)
            continue

        if is_header_row(cells):
            continue

        if is_footnote_row(cells):
            continue

        entry = _build_entry(cells, current_group)
        if entry:
            entries.append(entry)

    return entries, current_group


def parse_pdf(pdf_path: str) -> list[FoodEntry]:
    """Extract all food entries from the VN FCT PDF."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed. Run: pip install pdfplumber>=0.11")
        sys.exit(1)

    path = Path(pdf_path)
    if not path.exists():
        logger.error("PDF not found: %s", pdf_path)
        sys.exit(1)

    all_entries: list[FoodEntry] = []
    current_group = "Other"
    seen_keys: set[str] = set()

    logger.info("Opening PDF: %s", path)
    with pdfplumber.open(path) as pdf:
        logger.info("Total pages: %d", len(pdf.pages))
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            if not tables:
                # Fallback: try to detect group headers from plain text
                text = page.extract_text() or ""
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped and len(stripped) < 80 and not any(c.isdigit() for c in stripped[:5]):
                        current_group = stripped
                continue

            for table in tables:
                new_entries, current_group = _process_table(table, current_group)
                for entry in new_entries:
                    # Dedup by name_vi within same source
                    key = f"vn_fct_pdf:{entry.name_vi.lower()}"
                    if key in seen_keys:
                        logger.debug("Duplicate skipped: %s", entry.name_vi)
                        continue
                    seen_keys.add(key)
                    all_entries.append(entry)

            if page_num % 10 == 0:
                logger.info("Processed page %d, entries so far: %d", page_num, len(all_entries))

    return all_entries


def _print_summary(entries: list[FoodEntry]) -> None:
    category_counts: Counter = Counter(e.category for e in entries)
    print(f"\nExtracted {len(entries)} food entries")
    print(f"Categories ({len(category_counts)}):")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    micro_count = sum(1 for e in entries if e.extra_nutrients)
    print(f"Entries with micronutrients: {micro_count} ({micro_count/len(entries)*100:.0f}%)" if entries else "")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse Vietnamese Food Composition Table PDF → JSON"
    )
    parser.add_argument("pdf_path", help="Path to VN FCT PDF file")
    parser.add_argument(
        "--output",
        default="scripts/data/vn_fct_foods.json",
        help="Output JSON path (default: scripts/data/vn_fct_foods.json)",
    )
    args = parser.parse_args()

    entries = parse_pdf(args.pdf_path)
    if not entries:
        logger.error("No entries extracted — check PDF structure and parsing logic")
        sys.exit(1)

    save_entries(entries, args.output)
    logger.info("Saved %d entries to %s", len(entries), args.output)
    _print_summary(entries)


if __name__ == "__main__":
    main()
