"""
Fix PostgreSQL sequences after MySQL→Postgres data loads.

Symptom:
  psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "<table>_pkey"
  DETAIL: Key (id)=(N) already exists.

Cause:
  Data was copied with explicit integer `id` values, but the PostgreSQL sequence
  for that table was not advanced to MAX(id).

Usage:
  DATABASE_URL="postgresql://..." python scripts/fix_postgres_sequences.py
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text, Integer


def reset_postgres_sequences(pg_url: str) -> int:
    engine = create_engine(pg_url)
    insp = inspect(engine)
    tables = insp.get_table_names()
    fixed = 0

    with engine.begin() as conn:
        for table in tables:
            cols = insp.get_columns(table)
            id_col = next((c for c in cols if c.get("name") == "id"), None)
            if not id_col or not isinstance(id_col.get("type"), Integer):
                continue

            seq = conn.execute(
                text("SELECT pg_get_serial_sequence(:tbl, :col)"),
                {"tbl": table, "col": "id"},
            ).scalar()
            if not seq:
                continue

            conn.execute(
                text(
                    """
                    SELECT setval(
                      :seq,
                      GREATEST((SELECT COALESCE(MAX(id), 0) FROM {tbl}), 1),
                      (SELECT COALESCE(MAX(id), 0) FROM {tbl}) > 0
                    )
                    """.format(tbl=table)
                ),
                {"seq": seq},
            )
            fixed += 1

    return fixed


def main() -> None:
    pg_url = os.getenv("DATABASE_URL")
    if not pg_url:
        print("ERROR: DATABASE_URL is not set.")
        sys.exit(1)

    fixed = reset_postgres_sequences(pg_url)
    print(f"✅ PostgreSQL sequences reset for {fixed} table(s).")


if __name__ == "__main__":
    main()

