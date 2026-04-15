"""
Seed meal names into the pending_meal_image_resolution queue.

The nightly cron (resolve_pending_images.py) will pick these up, find/generate
images, compute CLIP embeddings, and store the results in meal_image_cache.

You can optionally supply a known image URL per meal — the cron will skip the
web-search step and go straight to CLIP validation for that row.

Usage (run from the mealtrack_backend root):
    # From a CSV file:
    python scripts/seed_meal_images.py --csv scripts/data/meal_images_seed.csv

    # Inline meal names:
    python scripts/seed_meal_images.py --meals "Pho Bo" "Banh Mi" "Com Tam"

    # Dry-run (print rows, do not write):
    python scripts/seed_meal_images.py --csv scripts/data/meal_images_seed.csv --dry-run

CSV format (header row required):
    meal_name,image_url,thumbnail_url,source
    Pho Bo,https://...,...,pexels
    Banh Mi,,,          <- image_url blank: cron will search automatically
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_module(rel_path: str, module_name: str):
    """Import a .py file directly, bypassing package __init__ chains."""
    path = os.path.join(_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_csv(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("meal_name", "").strip()
            if not name:
                continue
            rows.append(
                {
                    "meal_name": name,
                    "image_url": row.get("image_url", "").strip() or None,
                    "thumbnail_url": row.get("thumbnail_url", "").strip() or None,
                    "source": row.get("source", "").strip() or None,
                }
            )
    return rows


def _parse_inline(names: list[str]) -> list[dict]:
    return [
        {
            "meal_name": n.strip(),
            "image_url": None,
            "thumbnail_url": None,
            "source": None,
        }
        for n in names
        if n.strip()
    ]


def seed(rows: list[dict], dry_run: bool = False) -> None:
    slug = _load_module(
        "src/domain/services/meal_image_cache/name_canonicalizer.py",
        "name_canonicalizer",
    ).slug

    validated: list[dict] = []
    for row in rows:
        try:
            name_slug = slug(row["meal_name"])
        except ValueError as e:
            logger.warning("Skipping %r: %s", row["meal_name"], e)
            continue
        validated.append({**row, "name_slug": name_slug})

    if not validated:
        logger.warning("No valid rows to seed.")
        return

    if dry_run:
        logger.info("DRY RUN — would enqueue %d item(s):", len(validated))
        for row in validated:
            logger.info("  %-40s  image=%s", row["meal_name"], row["image_url"] or "(none)")
        return

    # Use psycopg2 directly — avoids importing the ORM model stack entirely
    import psycopg2

    db_url = os.getenv("DATABASE_URL", "")
    # Strip SQLAlchemy driver prefix if present
    db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    for row in validated:
        cur.execute(
            """
            INSERT INTO pending_meal_image_resolution
              (name_slug, meal_name, candidate_image_url, candidate_thumbnail_url, candidate_source)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name_slug) DO NOTHING
            """,
            (
                row["name_slug"],
                row["meal_name"],
                row["image_url"],
                row["thumbnail_url"],
                row["source"],
            ),
        )
        if cur.rowcount:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()

    logger.info("Done: %d inserted, %d already existed.", inserted, skipped)
    logger.info("Run `python scripts/resolve_pending_images.py` to process them.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed meal names into the image resolver queue.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", metavar="FILE", help="Path to CSV file (see script docstring for format)")
    source.add_argument("--meals", nargs="+", metavar="NAME", help="One or more meal names (quoted)")
    parser.add_argument("--dry-run", action="store_true", help="Print rows without writing to DB")
    args = parser.parse_args()

    if args.csv:
        rows = _parse_csv(args.csv)
        logger.info("Parsed %d row(s) from %s", len(rows), args.csv)
    else:
        rows = _parse_inline(args.meals)
        logger.info("Parsed %d inline meal(s)", len(rows))

    seed(rows, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
