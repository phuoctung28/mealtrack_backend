#!/usr/bin/env python3
"""Delete orphan Meal rows that were created by the legacy caloric-drink dual-write.

These are meals where:
  meal_type = 'hydration'
  AND meal_id IN (SELECT legacy_meal_id FROM hydration_entries WHERE legacy_meal_id IS NOT NULL)

The hydration_entries rows are the source of truth; the linked Meal rows are
legacy stubs that exist only for backward compatibility and are safe to remove
once Phase 3c (unified feed) is live.

Usage:
    python scripts/development/cleanup_orphan_hydration_meal_rows.py          # dry-run
    python scripts/development/cleanup_orphan_hydration_meal_rows.py --execute # delete
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    try:
        from src.infra.database.config import SQLALCHEMY_DATABASE_URL
        DATABASE_URL = SQLALCHEMY_DATABASE_URL
    except Exception:
        pass

if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL env var or ensure src.infra.database.config is importable.")
    sys.exit(1)

# Use sync engine for a one-shot script
SYNC_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

COUNT_SQL = text("""
    SELECT COUNT(*)
    FROM meal
    WHERE meal_type = 'hydration'
      AND meal_id IN (
          SELECT legacy_meal_id
          FROM hydration_entries
          WHERE legacy_meal_id IS NOT NULL
      )
""")

DELETE_SQL = text("""
    DELETE FROM meal
    WHERE meal_type = 'hydration'
      AND meal_id IN (
          SELECT legacy_meal_id
          FROM hydration_entries
          WHERE legacy_meal_id IS NOT NULL
      )
""")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete rows (default is dry-run).",
    )
    args = parser.parse_args()

    engine = create_engine(SYNC_URL)
    with engine.connect() as conn:
        count = conn.execute(COUNT_SQL).scalar_one()
        print(f"Orphan hydration meal rows found: {count}")

        if count == 0:
            print("Nothing to clean up.")
            return

        if args.execute:
            result = conn.execute(DELETE_SQL)
            conn.commit()
            print(f"Deleted {result.rowcount} rows from meal table.")
        else:
            print("Dry-run — pass --execute to delete.")


if __name__ == "__main__":
    main()
