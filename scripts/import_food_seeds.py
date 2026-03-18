"""Import food seed JSON into food_reference. Use --fetch to download from APIs first."""
import argparse
import json
import logging
import subprocess
import sys
import unicodedata
from pathlib import Path

# Allow running from backend/ root: python -m scripts.import_food_seeds
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SOURCE_PRIORITY: dict[str, int] = {
    "nin_vn": 1,
    "vn_fct_pdf": 2,
    "openfoodfacts": 3,
    "ttytyenlac": 4,
}
_DEFAULT_PRIORITY = 99
_SCRAPERS_DIR = Path(__file__).resolve().parent / "scrapers"


def _normalize_name(text: str) -> str:
    """NFC-normalize and lowercase for dedup comparison."""
    return unicodedata.normalize("NFC", text.strip()).lower()


def _load_json_file(path: Path) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning("Skipping %s — expected JSON array", path.name)
            return []
        return data
    except Exception as e:
        logger.error("Failed to load %s: %s", path.name, e)
        return []


def _validate_entry(entry: dict) -> list[str]:
    """Return list of warning strings; empty = valid."""
    warnings: list[str] = []
    for field in ("protein_100g", "carbs_100g", "fat_100g"):
        val = entry.get(field, 0) or 0
        if val < 0:
            warnings.append(f"{field} is negative: {val}")
    macro_sum = (
        (entry.get("protein_100g") or 0)
        + (entry.get("carbs_100g") or 0)
        + (entry.get("fat_100g") or 0)
    )
    if macro_sum > 100:
        warnings.append(f"Macro sum {macro_sum:.1f}g exceeds 100g/100g")
    if not entry.get("name_vi") and entry.get("region", "VN") == "VN":
        warnings.append("name_vi is missing for VN-sourced food")
    return warnings


def _dedup_entries(all_entries: list[dict], source_filter: str | None) -> list[dict]:
    """Keep highest-priority source per normalized name_vi. Barcoded entries kept as-is."""
    barcoded: list[dict] = []
    by_name: dict[str, dict] = {}
    for entry in all_entries:
        source = entry.get("source", "")
        if source_filter and source != source_filter:
            continue

        if entry.get("barcode"):
            barcoded.append(entry)
            continue

        name_vi = entry.get("name_vi") or entry.get("name") or ""
        key = _normalize_name(name_vi)
        if not key:
            barcoded.append(entry)
            continue

        existing = by_name.get(key)
        if existing is None:
            by_name[key] = entry
        else:
            existing_pri = SOURCE_PRIORITY.get(existing.get("source", ""), _DEFAULT_PRIORITY)
            new_pri = SOURCE_PRIORITY.get(source, _DEFAULT_PRIORITY)
            if new_pri < existing_pri:
                by_name[key] = entry

    return barcoded + list(by_name.values())


def _fetch_data(data_dir: Path) -> None:
    """Fetch seed data from NIN VN + OpenFoodFacts APIs into data_dir."""
    data_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable

    fetchers = [
        ("NIN VN", [python, str(_SCRAPERS_DIR / "fetch_nin_vn.py"),
                    "--output-foods", str(data_dir / "nin_vn_foods.json"),
                    "--output-dishes", str(data_dir / "nin_vn_dishes.json")]),
        ("OpenFoodFacts VN", [python, str(_SCRAPERS_DIR / "fetch_off_vn.py"),
                              "--output", str(data_dir / "off_vn_products.json")]),
    ]
    for label, cmd in fetchers:
        logger.info("Fetching %s ...", label)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("Fetch failed for %s:\n%s", label, result.stderr[-500:])
        else:
            logger.info("Fetched %s successfully", label)


def _run_import(data_dir: Path, dry_run: bool, source_filter: str | None) -> None:
    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        logger.warning("No JSON files found in %s", data_dir)
        return

    logger.info("Loading from %d JSON file(s) in %s", len(json_files), data_dir)
    all_entries: list[dict] = []
    for path in json_files:
        entries = _load_json_file(path)
        logger.info("  %s → %d entries", path.name, len(entries))
        all_entries.extend(entries)

    logger.info("Total loaded: %d entries", len(all_entries))
    deduped = _dedup_entries(all_entries, source_filter)
    logger.info("After dedup: %d entries", len(deduped))

    counts: dict[str, int] = {"inserted": 0, "updated": 0, "skipped": 0, "invalid": 0}
    if dry_run:
        logger.info("Dry-run mode — validating only, no DB writes")

    repo = None
    if not dry_run:
        from src.infra.repositories.food_reference_repository import FoodReferenceRepository
        repo = FoodReferenceRepository()

    for entry in deduped:
        warnings = _validate_entry(entry)
        if warnings:
            critical = [w for w in warnings if "negative" in w or "exceeds" in w]
            if critical:
                counts["invalid"] += 1
                continue

        if dry_run:
            counts["inserted"] += 1
            continue

        result = repo.upsert_seed(entry)  # type: ignore[union-attr]
        counts[result] += 1

    _print_report(counts, dry_run)


def _print_report(counts: dict[str, int], dry_run: bool) -> None:
    mode = " (dry-run)" if dry_run else ""
    total = sum(counts.values())
    print(f"\nImport report{mode}:")
    print(f"  Total processed : {total}")
    print(f"  Inserted        : {counts['inserted']}")
    print(f"  Updated         : {counts['updated']}")
    print(f"  Skipped (error) : {counts['skipped']}")
    print(f"  Invalid (macros): {counts['invalid']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and import VN food seed data into food_reference table."
    )
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch data from NIN VN + OpenFoodFacts APIs before importing")
    parser.add_argument("--data-dir",
                        default=str(Path(__file__).resolve().parent / "data"),
                        help="Directory for JSON files (default: scripts/data/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate entries only — no DB writes")
    parser.add_argument("--source", default=None,
                        help="Import only entries from this source (e.g. 'nin_vn')")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    if args.fetch:
        _fetch_data(data_dir)

    if not data_dir.exists():
        logger.error("data-dir does not exist: %s — use --fetch to download data first", data_dir)
        sys.exit(1)

    _run_import(data_dir=data_dir, dry_run=args.dry_run, source_filter=args.source)


if __name__ == "__main__":
    main()
