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
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


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


def _load_slug():
    """Load slug() without triggering package __init__ chains."""
    import importlib.util as _ilu
    _path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "domain", "services", "meal_image_cache", "name_canonicalizer.py",
    )
    _spec = _ilu.spec_from_file_location("name_canonicalizer", _path)
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod.slug


def seed(rows: list[dict], dry_run: bool = False) -> None:
    slug = _load_slug()

    # Normalise + slug each row first (no DB imports needed yet)
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

    # Only import heavy DB/model stack when actually writing
    import asyncio
    from src.domain.model.meal_image_cache import PendingItem
    from src.infra.database.config import SessionLocal
    from src.infra.repositories.pending_meal_image_repository import (
        PendingMealImageRepository,
    )

    items = [
        PendingItem(
            meal_name=row["meal_name"],
            name_slug=row["name_slug"],
            candidate_image_url=row["image_url"],
            candidate_thumbnail_url=row["thumbnail_url"],
            candidate_source=row["source"],
        )
        for row in validated
    ]

    with SessionLocal() as session:
        repo = PendingMealImageRepository(session)
        asyncio.run(repo.enqueue_many(items))

    logger.info("Enqueued %d item(s) into pending_meal_image_resolution.", len(items))
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
