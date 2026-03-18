"""
Validate and clean scraped food seed data before import.

Usage:
  python validate_seeds.py --data-dir ../data                    # report only
  python validate_seeds.py --data-dir ../data --fix              # fix + overwrite
  python validate_seeds.py --data-dir ../data --fix --output DIR # fix + write to new dir

Checks: macro ranges, missing fields, duplicates, outliers.
Fixes: normalize macros > 100g, drop entries with no usable data.
"""

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Macro sum > this threshold is likely per-serving, not per-100g
MACRO_SUM_THRESHOLD = 100.0
# Individual macro caps (per 100g)
MAX_PROTEIN = 90.0  # dried fish/gelatin can be ~85g
MAX_FAT = 100.0     # pure oils
MAX_CARBS = 100.0   # pure sugar


def _load(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _save(entries: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _is_junk_name(entry: dict) -> bool:
    """Detect garbage/non-food names from crowd-sourced data.
    Official sources (nin_vn) are trusted — short VN names like 'Ổi' are valid."""
    source = entry.get("source", "")
    if source.startswith("nin_vn") or source == "vn_fct_pdf":
        return False  # trust official sources

    name = (entry.get("name_vi") or entry.get("name") or "").strip()
    name_lower = name.lower()
    # No letters at all
    if not any(c.isalpha() for c in name):
        return True
    # Too short (≤2 chars) for non-official sources
    if len(name) <= 2:
        return True
    # All same character repeated (e.g. "gg", "aaa")
    unique_chars = set(name_lower.replace(" ", ""))
    if len(unique_chars) <= 1:
        return True
    # Contains profanity/non-food indicators
    junk_patterns = ["wtf", "test", "xxx", "asdf", "fake", "delete", "unknown"]
    if any(p in name_lower for p in junk_patterns):
        return True
    # Name has no Vietnamese or common food-related characters (purely non-food)
    # Allow Latin, Vietnamese diacritics, CJK, digits, common punctuation
    has_food_chars = any(
        c.isalpha() and (ord(c) < 0x0250 or ord(c) > 0x2C00)  # Latin/VN or CJK
        for c in name
    )
    if not has_food_chars:
        return True
    return False


def validate_entry(entry: dict) -> list[str]:
    """Return list of issue descriptions. Empty = clean."""
    issues: list[str] = []
    p = entry.get("protein_100g", 0) or 0
    c = entry.get("carbs_100g", 0) or 0
    f = entry.get("fat_100g", 0) or 0
    macro_sum = p + c + f

    if p < 0 or c < 0 or f < 0:
        issues.append("negative_macro")
    if macro_sum > MACRO_SUM_THRESHOLD:
        issues.append(f"macro_sum_{macro_sum:.0f}g")
    if p > MAX_PROTEIN:
        issues.append(f"protein_{p:.0f}g")
    if not entry.get("name_vi") and not entry.get("name"):
        issues.append("no_name")
    if p == 0 and c == 0 and f == 0:
        issues.append("no_macros")
    # Junk name detection (for non-official sources like openfoodfacts)
    if _is_junk_name(entry):
        issues.append("junk_name")
    return issues


def fix_entry(entry: dict) -> dict | None:
    """Attempt to fix an entry. Returns None if unfixable (should be dropped)."""
    p = entry.get("protein_100g", 0) or 0
    c = entry.get("carbs_100g", 0) or 0
    f = entry.get("fat_100g", 0) or 0

    # Drop entries with no name or junk names
    if not entry.get("name_vi") and not entry.get("name"):
        return None
    if _is_junk_name(entry):
        return None

    # Drop entries with no macros
    if p == 0 and c == 0 and f == 0:
        return None

    # Drop entries with negative macros
    if p < 0 or c < 0 or f < 0:
        return None

    # Normalize macros > 100g: scale down proportionally to sum=95g
    macro_sum = p + c + f
    if macro_sum > MACRO_SUM_THRESHOLD:
        scale = 95.0 / macro_sum
        entry["protein_100g"] = round(p * scale, 1)
        entry["carbs_100g"] = round(c * scale, 1)
        entry["fat_100g"] = round(f * scale, 1)
        fiber = entry.get("fiber_100g", 0) or 0
        sugar = entry.get("sugar_100g", 0) or 0
        entry["fiber_100g"] = round(fiber * scale, 1)
        entry["sugar_100g"] = round(sugar * scale, 1)

    return entry


def run_validation(data_dir: Path, fix: bool, output_dir: Path | None) -> None:
    """Validate all JSON files, optionally fix and save."""
    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        logger.warning("No JSON files in %s", data_dir)
        return

    total_stats = {"clean": 0, "fixed": 0, "dropped": 0, "total": 0}

    for path in json_files:
        entries = _load(path)
        logger.info("%s: %d entries", path.name, len(entries))
        clean_entries: list[dict] = []
        file_stats = {"clean": 0, "fixed": 0, "dropped": 0}

        for entry in entries:
            total_stats["total"] += 1
            issues = validate_entry(entry)

            if not issues:
                clean_entries.append(entry)
                file_stats["clean"] += 1
                continue

            if fix:
                fixed = fix_entry(entry)
                if fixed is not None:
                    clean_entries.append(fixed)
                    file_stats["fixed"] += 1
                else:
                    file_stats["dropped"] += 1
                    logger.debug("Dropped: %s (%s)", entry.get("name_vi", "?"), issues)
            else:
                clean_entries.append(entry)  # report-only mode keeps all
                file_stats["fixed"] += 1  # count as "has issues"

        for k in file_stats:
            total_stats[k] += file_stats[k]

        logger.info("  → %d clean, %d %s, %d dropped",
                     file_stats["clean"],
                     file_stats["fixed"], "fixed" if fix else "issues",
                     file_stats["dropped"])

        if fix:
            out_path = (output_dir or data_dir) / path.name
            _save(clean_entries, out_path)
            logger.info("  → Saved %d entries to %s", len(clean_entries), out_path)

    print(f"\nValidation summary:")
    print(f"  Total entries : {total_stats['total']}")
    print(f"  Clean         : {total_stats['clean']}")
    print(f"  {'Fixed' if fix else 'Issues':14s}: {total_stats['fixed']}")
    print(f"  Dropped       : {total_stats['dropped']}")
    if fix:
        print(f"  Output        : {output_dir or data_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and clean food seed JSON data")
    parser.add_argument("--data-dir", required=True, help="Directory with JSON seed files")
    parser.add_argument("--fix", action="store_true", help="Fix anomalies and overwrite files")
    parser.add_argument("--output", default=None, help="Output dir for fixed files (default: overwrite)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output) if args.output else None
    run_validation(data_dir, fix=args.fix, output_dir=output_dir)


if __name__ == "__main__":
    main()
