"""Import food seed JSON into food_reference. Use --fetch to download from APIs first."""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

# Allow running from backend/ root: python -m scripts.import_food_seeds
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from src.domain.services.meal_suggestion.ingredient_name_normalizer import (
    normalize_food_name,
)
from src.infra.database.uow_async import AsyncUnitOfWork

SOURCE_PRIORITY: dict[str, int] = {
    "nin_vn": 1,
    "vn_fct_pdf": 2,
    "openfoodfacts": 3,
    "ttytyenlac": 4,
}
_DEFAULT_PRIORITY = 99
_SCRAPERS_DIR = Path(__file__).resolve().parent / "scrapers"
_TRUSTED_SEED_SOURCES = frozenset({"nin_vn", "vn_fct_pdf"})


def _normalize_name(text: str) -> str:
    """NFC-normalize and lowercase for dedup comparison."""
    return unicodedata.normalize("NFC", text.strip()).lower()


def _load_json_file(path: Path) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
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
            existing_pri = SOURCE_PRIORITY.get(
                existing.get("source", ""), _DEFAULT_PRIORITY
            )
            new_pri = SOURCE_PRIORITY.get(source, _DEFAULT_PRIORITY)
            if new_pri < existing_pri:
                by_name[key] = entry

    return barcoded + list(by_name.values())


def _fetch_data(data_dir: Path) -> None:
    """Fetch seed data from NIN VN + OpenFoodFacts APIs into data_dir."""
    data_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable

    fetchers = [
        (
            "NIN VN",
            [
                python,
                str(_SCRAPERS_DIR / "fetch_nin_vn.py"),
                "--output-foods",
                str(data_dir / "nin_vn_foods.json"),
                "--output-dishes",
                str(data_dir / "nin_vn_dishes.json"),
            ],
        ),
        (
            "OpenFoodFacts VN",
            [
                python,
                str(_SCRAPERS_DIR / "fetch_off_vn.py"),
                "--output",
                str(data_dir / "off_vn_products.json"),
            ],
        ),
    ]
    for label, cmd in fetchers:
        logger.info("Fetching %s ...", label)
        result = subprocess.run(cmd, text=True)  # streams stdout/stderr live
        if result.returncode != 0:
            logger.error("Fetch failed for %s (exit code %d)", label, result.returncode)
        else:
            logger.info("Fetched %s successfully", label)


def _fetch_nin_dishes(data_dir: Path) -> bool:
    """Fetch only the NIN prepared-dishes catalog into an isolated directory."""
    output_path = data_dir / "nin_vn_dishes.json"
    command = [
        sys.executable,
        str(_SCRAPERS_DIR / "fetch_nin_vn.py"),
        "--dishes-only",
        "--output-dishes",
        str(output_path),
    ]
    logger.info("Fetching NIN VN dishes ...")
    result = subprocess.run(command, text=True)
    if result.returncode != 0:
        logger.error("Failed to fetch NIN VN dishes (exit code %d)", result.returncode)
        return False
    return output_path.exists()


async def _run_import(data_dir: Path, dry_run: bool, source_filter: str | None) -> None:
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

    if dry_run:
        for entry in deduped:
            if _is_invalid(entry):
                counts["invalid"] += 1
            else:
                counts["inserted"] += 1
        _print_report(counts, dry_run)
        return

    async with AsyncUnitOfWork() as uow:
        total = len(deduped)
        for i, entry in enumerate(deduped, 1):
            if _is_invalid(entry):
                counts["invalid"] += 1
                continue
            result = await _upsert_entry(uow.food_references, entry)
            counts[result] += 1

            if i % 100 == 0 or i == total:
                done = sum(counts.values())
                logger.info(
                    "Progress: %d/%d (%d inserted, %d updated, %d skipped)",
                    done,
                    total,
                    counts["inserted"],
                    counts["updated"],
                    counts["skipped"],
                )

    _print_report(counts, dry_run)


def _is_invalid(entry: dict) -> bool:
    warnings = _validate_entry(entry)
    return not _entry_name(entry) or any(
        "negative" in warning or "exceeds" in warning for warning in warnings
    )


async def _upsert_entry(repository, entry: dict) -> str:
    if entry.get("barcode"):
        existing = await repository.get_by_barcode(entry["barcode"])
        await repository.upsert(_prepared_entry(entry))
        return "updated" if existing is not None else "inserted"

    prepared = _prepared_entry(entry)
    existing = await repository.find_by_normalized_name(prepared["name_normalized"])
    if existing is not None and _existing_wins(existing, prepared):
        return "skipped"
    await repository.upsert_seed(prepared)
    return "updated" if existing is not None else "inserted"


def _prepared_entry(entry: dict) -> dict:
    prepared = dict(entry)
    prepared["name"] = _entry_name(entry)
    prepared["name_normalized"] = normalize_food_name(prepared["name"])
    prepared["is_verified"] = entry.get("source") in _TRUSTED_SEED_SOURCES
    return prepared


def _existing_wins(existing: dict, incoming: dict) -> bool:
    existing_source = existing.get("source")
    incoming_source = incoming.get("source")
    existing_priority = _source_priority(existing_source)
    incoming_priority = _source_priority(incoming_source)
    if existing.get("is_verified"):
        if existing_source not in _TRUSTED_SEED_SOURCES:
            return True
        return existing_priority <= incoming_priority
    return existing_priority < incoming_priority


def _source_priority(source: str | None) -> int:
    return SOURCE_PRIORITY.get(source or "", _DEFAULT_PRIORITY)


def _entry_name(entry: dict) -> str:
    return str(entry.get("name") or entry.get("name_vi") or "").strip()


def _print_report(counts: dict[str, int], dry_run: bool) -> None:
    mode = " (dry-run)" if dry_run else ""
    print(
        f"\nImport report{mode}: {sum(counts.values())} total — "
        f"{counts['inserted']} inserted, {counts['updated']} updated, "
        f"{counts['skipped']} skipped, {counts['invalid']} invalid"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and import VN food seeds.")
    parser.add_argument(
        "--fetch", action="store_true", help="Fetch from APIs before importing"
    )
    parser.add_argument(
        "--fetch-nin-dishes",
        action="store_true",
        help="Fetch and import only the NIN prepared-dishes catalog",
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip validation report"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Explicitly rewrite invalid seed files"
    )
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).resolve().parent / "data"),
        help="JSON files directory (default: scripts/data/)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate only, no DB writes"
    )
    parser.add_argument(
        "--source", default=None, help="Filter by source (e.g. 'nin_vn')"
    )
    args = parser.parse_args()

    if args.fetch_nin_dishes:
        with tempfile.TemporaryDirectory(prefix="nutree-nin-dishes-") as temp_dir:
            if not _fetch_nin_dishes(Path(temp_dir)):
                sys.exit(1)
            asyncio.run(
                _run_import(
                    data_dir=Path(temp_dir),
                    dry_run=args.dry_run,
                    source_filter="nin_vn",
                )
            )
        return

    data_dir = Path(args.data_dir)

    if args.fetch:
        _fetch_data(data_dir)

    if not args.no_validate and data_dir.exists():
        logger.info("Validating seed data...")
        command = [
            sys.executable,
            str(_SCRAPERS_DIR / "validate_seeds.py"),
            "--data-dir",
            str(data_dir),
        ]
        if args.fix:
            command.append("--fix")
        subprocess.run(command, text=True, check=False)

    if not data_dir.exists():
        logger.error(
            "data-dir does not exist: %s — use --fetch to download data first", data_dir
        )
        sys.exit(1)

    asyncio.run(
        _run_import(data_dir=data_dir, dry_run=args.dry_run, source_filter=args.source)
    )


if __name__ == "__main__":
    main()
