"""
MySQL → PostgreSQL data migration script.

Copies all rows from MySQL into the already-initialised PostgreSQL (Neon) schema.
Run AFTER init_postgres_db.py has created all tables in PostgreSQL.

Usage:
    pip install pymysql  # one-time, for this script only
    python scripts/init_postgres_db.py   # ensure schema exists first
    python scripts/migrate_mysql_to_postgres.py

Environment variables (or hardcode below):
    MYSQL_URL       mysql+pymysql://user:pass@host:port/dbname
    DATABASE_URL    postgresql://...  (Neon direct URL, not pooled)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Connection strings (from .env) ────────────────────────────────────────────
MYSQL_URL = os.getenv("MYSQL_URL")
if not MYSQL_URL:
    print("ERROR: MYSQL_URL environment variable is required.")
    print("  Set it in .env or export before running.")
    sys.exit(1)

PG_URL = os.getenv("DATABASE_URL")
if not PG_URL:
    print("ERROR: DATABASE_URL environment variable is required.")
    print("  Set it in .env or export before running.")
    sys.exit(1)

# MySQL table name → PostgreSQL table name (when they differ)
# Current prod schema uses the same names on both sides; keep legacy aliases for safety.
TABLE_NAME_MAP = {
    # legacy aliases
    "profiles": "user_profiles",
    "meal_translations": "meal_translation",
    "food_item_translations": "food_item_translation",
    "barcode_products": "food_reference",
}

# Tables to migrate, in dependency order (parents before children).
# Use MySQL table names here.
#
# Expected schema (both MySQL and Postgres) from production:
# ['cheat_days','feature_flags','food_item','food_item_translation','food_reference','meal',
#  'meal_translation','mealimage','notification_preferences','nutrition','saved_suggestions',
#  'subscriptions','user_fcm_tokens','user_profiles','users','weekly_macro_budgets', 'alembic_version']
#
# NOTE: alembic_version is intentionally not migrated (it is environment-specific).
TABLES = [
    "users",
    "user_profiles",
    "subscriptions",
    "mealimage",
    "meal",
    "nutrition",
    "food_reference",
    "food_item",
    "meal_translation",
    "food_item_translation",
    "notification_preferences",
    "user_fcm_tokens",
    "cheat_days",
    "weekly_macro_budgets",
    "saved_suggestions",
    "feature_flags",
]

# ── Imports ───────────────────────────────────────────────────────────────────
try:
    import pymysql  # noqa: F401
except ImportError:
    print("ERROR: pymysql not installed. Run: pip install pymysql")
    sys.exit(1)

from sqlalchemy import create_engine, inspect, text
from sqlalchemy import Integer
from sqlalchemy.types import Boolean


def get_tables(engine):
    return set(inspect(engine).get_table_names())


def get_bool_columns(engine, table: str) -> set:
    """Return column names that should be treated as boolean in PostgreSQL."""
    cols = inspect(engine).get_columns(table)
    bool_cols = set()
    for c in cols:
        t = c.get("type")
        if t is None:
            continue
        # SQLAlchemy dialects sometimes return subclasses; python_type is the most robust.
        try:
            if getattr(t, "python_type", None) is bool:
                bool_cols.add(c["name"])
                continue
        except Exception:
            pass
        if isinstance(t, Boolean):
            bool_cols.add(c["name"])
    return bool_cols


def cast_bools(rows, bool_cols: set) -> list:
    """Convert MySQL 0/1 integers to Python bool for boolean columns."""
    result = []
    for row in rows:
        r = dict(row)
        for col in bool_cols:
            if col in r and r[col] is not None:
                r[col] = bool(r[col])
        result.append(r)
    return result


def migrate_table(mysql_table: str, pg_table: str, src_engine, dst_engine):
    with src_engine.connect() as src:
        rows = src.execute(text(f"SELECT * FROM `{mysql_table}`")).mappings().all()

    if not rows:
        print(f"  {mysql_table}: 0 rows (skipped)")
        return

    # Make the script idempotent by default: if destination already has data,
    # skip copying (prevents duplicate key failures on reruns).
    with dst_engine.connect() as dst:
        existing = dst.execute(text(f"SELECT 1 FROM {pg_table} LIMIT 1")).first()
        if existing is not None:
            print(f"  {mysql_table}: already has data in {pg_table} (skipped)")
            return

    bool_cols = get_bool_columns(dst_engine, pg_table)
    rows_converted = cast_bools(rows, bool_cols)

    with dst_engine.begin() as dst:
        cols = list(rows_converted[0].keys())
        col_list = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join(f":{c}" for c in cols)
        dst.execute(
            text(f"INSERT INTO {pg_table} ({col_list}) VALUES ({placeholders})"),
            rows_converted,
        )

    label = mysql_table if mysql_table == pg_table else f"{mysql_table} → {pg_table}"
    print(f"  {label}: {len(rows_converted)} rows copied")


def reset_postgres_sequences(engine) -> None:
    """
    After copying rows with explicit integer IDs, PostgreSQL sequences can lag behind.
    This resets any `id` sequences to `MAX(id)` so future inserts don't hit UniqueViolation.
    """
    insp = inspect(engine)
    tables = insp.get_table_names()
    fixed = 0

    with engine.begin() as conn:
        for table in tables:
            cols = insp.get_columns(table)
            id_col = next((c for c in cols if c.get("name") == "id"), None)
            if not id_col:
                continue
            if not isinstance(id_col.get("type"), Integer):
                continue

            seq = conn.execute(
                text("SELECT pg_get_serial_sequence(:tbl, :col)"),
                {"tbl": table, "col": "id"},
            ).scalar()
            if not seq:
                continue

            # If table is empty, set sequence to 1 (nextval will return 1).
            # If not empty, set it to MAX(id).
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

    print(f"\nPostgreSQL sequences reset: {fixed} table(s) updated.")


def main():
    print("Connecting to MySQL...")
    src_engine = create_engine(
        MYSQL_URL,
        connect_args={"ssl": {"check_hostname": False, "verify_mode": 0}},
    )

    print("Connecting to PostgreSQL...")
    dst_engine = create_engine(PG_URL)

    src_tables = get_tables(src_engine)
    dst_tables = get_tables(dst_engine)

    print(f"\nMySQL tables found:      {len(src_tables)}")
    print(f"PostgreSQL tables found: {len(dst_tables)}")
    print(f"MySQL tables: {sorted(src_tables)}")
    print()

    skipped = []
    to_migrate = []
    for mysql_tbl in TABLES:
        pg_tbl = TABLE_NAME_MAP.get(mysql_tbl, mysql_tbl)
        if mysql_tbl not in src_tables:
            skipped.append(f"{mysql_tbl} (not in MySQL)")
        elif pg_tbl not in dst_tables:
            skipped.append(f"{mysql_tbl} → {pg_tbl} (not in PostgreSQL)")
        else:
            to_migrate.append((mysql_tbl, pg_tbl))

    if skipped:
        print(f"Skipping:\n  " + "\n  ".join(skipped) + "\n")

    print("Starting migration...\n")
    errors = []
    for mysql_tbl, pg_tbl in to_migrate:
        try:
            migrate_table(mysql_tbl, pg_tbl, src_engine, dst_engine)
        except Exception as e:
            print(f"  {mysql_tbl}: ERROR — {e}")
            errors.append((mysql_tbl, str(e)))

    print()
    if errors:
        print(f"Completed with {len(errors)} error(s):")
        for t, e in errors:
            print(f"  {t}: {e}")
        sys.exit(1)
    else:
        print("Migration complete — all tables copied successfully.")
        reset_postgres_sequences(dst_engine)


if __name__ == "__main__":
    main()
