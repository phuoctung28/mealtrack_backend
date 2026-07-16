"""Validate catalog recipe seed manifests before release import."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain.services.meal_recommendation.catalog_recipe_seed_validator import (
    PRODUCTION_CUISINE_COUNTS,
    validate_catalog_seed_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate meal recommendation catalog recipe seeds."
    )
    parser.add_argument(
        "--manifest",
        default=str(Path(__file__).resolve().parent / "data" / "meal-recommendation-recipes.json"),
        help="Catalog recipe seed manifest JSON path.",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=180,
        help="Expected recipe count. Production default is 180.",
    )
    parser.add_argument(
        "--min-per-cuisine-meal-type",
        type=int,
        default=5,
        help="Minimum eligible recipes for each cuisine and meal type.",
    )
    parser.add_argument(
        "--skip-exact-cuisine-count",
        action="store_true",
        help="Disable production 60/60/60 cuisine split validation for fixtures.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only. This command does not write to the database yet.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    result = validate_catalog_seed_manifest(
        manifest,
        expected_recipe_count=args.expected_count,
        min_per_cuisine_meal_type=args.min_per_cuisine_meal_type,
        expected_cuisine_counts=(
            None if args.skip_exact_cuisine_count else PRODUCTION_CUISINE_COUNTS
        ),
    )

    print(f"manifest_digest={result.manifest_digest}")
    print(f"recipe_count={result.recipe_count}")
    for cuisine, meal_counts in sorted(result.coverage.items()):
        print(f"coverage[{cuisine}]={meal_counts}")

    if result.errors:
        print("validation=failed")
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        sys.exit(1)

    print("validation=passed")
    if not args.dry_run:
        print("db_import=not_implemented; run with --dry-run for Phase 3 validation")


if __name__ == "__main__":
    main()
