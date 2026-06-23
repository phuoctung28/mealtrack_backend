"""
One-shot script: delete meal rows that were created as dual-write stubs by
LogCaloricDrinkCommandHandler before Phase 3d removed the dual-write.

Identifies orphans as: meals WHERE meal_type = 'hydration'
  AND meal_id IN (SELECT legacy_meal_id FROM hydration_entries WHERE legacy_meal_id IS NOT NULL)

Run with --execute to actually delete; default is dry-run.

Usage:
    python scripts/development/cleanup_orphan_hydration_meal_rows.py
    python scripts/development/cleanup_orphan_hydration_meal_rows.py --execute
"""

import argparse
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def main(execute: bool) -> None:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not db_url:
        print("ERROR: DATABASE_URL or POSTGRES_URL env var not set", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    count_sql = """
        SELECT COUNT(*)
        FROM meals
        WHERE meal_type = 'hydration'
          AND meal_id IN (
              SELECT legacy_meal_id
              FROM hydration_entries
              WHERE legacy_meal_id IS NOT NULL
          )
    """
    cur.execute(count_sql)
    count = cur.fetchone()[0]
    print(f"Orphan hydration meal rows found: {count}")

    if count == 0:
        print("Nothing to delete.")
        conn.close()
        return

    if not execute:
        print("DRY RUN — pass --execute to delete.")
        conn.close()
        return

    delete_sql = """
        DELETE FROM meals
        WHERE meal_type = 'hydration'
          AND meal_id IN (
              SELECT legacy_meal_id
              FROM hydration_entries
              WHERE legacy_meal_id IS NOT NULL
          )
    """
    cur.execute(delete_sql)
    deleted = cur.rowcount
    conn.commit()
    print(f"Deleted {deleted} orphan rows.")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete rows (default is dry-run)",
    )
    args = parser.parse_args()
    main(execute=args.execute)
