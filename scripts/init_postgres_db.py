"""
PostgreSQL / Neon database initialisation script.

Use this instead of `alembic upgrade head` when setting up a fresh PostgreSQL
database. It:
  1. Creates the pgvector extension
  2. Creates all tables from the current SQLAlchemy models
  3. Stamps Alembic so future `alembic upgrade head` calls only run NEW migrations

Safe to run multiple times — it skips setup if tables already exist.

Usage:
    python scripts/init_postgres_db.py

Environment:
    DATABASE_URL  — Neon direct connection string (not pooled)
                    e.g. postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
"""

import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

# Override DATABASE_URL before importing the engine so it picks up the direct
# connection string (MIGRATION_DATABASE_URL) if provided.
migration_url = os.getenv("MIGRATION_DATABASE_URL") or os.getenv("DATABASE_URL")
if not migration_url:
    print("ERROR: DATABASE_URL is not set.")
    sys.exit(1)

os.environ["DATABASE_URL"] = migration_url

from src.infra.database.config import engine, Base  # noqa: E402 — must come after env override

# Import every model so they register themselves on Base.metadata
import src.infra.database.models  # noqa: F401, E402


def db_is_fresh() -> bool:
    """Return True if no application tables exist yet."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    app_tables = [t for t in tables if t != "alembic_version"]
    return len(app_tables) == 0


def get_current_alembic_revision() -> str | None:
    """
    Return current Alembic revision, if present.

    A partially initialised database can contain application tables but no
    `alembic_version` table/row (e.g. interrupted bootstrap). In that state,
    running `alembic upgrade head` from base replays revision 001 and fails with
    duplicate-table errors. We detect that and recover by stamping head.
    """
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None

    with engine.begin() as conn:
        return conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()


def stamp_alembic_head(cfg: Config) -> None:
    """
    Persist Alembic head revision metadata directly in the database.

    Some local setups can end up with application tables but no `alembic_version`.
    Writing the version row ourselves makes bootstrap recovery deterministic.
    """
    head_revision = ScriptDirectory.from_config(cfg).get_current_head()
    if not head_revision:
        raise RuntimeError("Unable to resolve Alembic head revision.")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                )
                """
            )
        )
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": head_revision},
        )


def main():
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", migration_url)

    if not db_is_fresh():
        revision = get_current_alembic_revision()
        if revision is None:
            print(
                "Database has tables but no Alembic revision metadata; "
                "stamping head to recover bootstrap state."
            )
            stamp_alembic_head(cfg)
            print("Done.")
            return

        print("Database already initialised — running alembic upgrade head for any new migrations.")
        command.upgrade(cfg, "head")
        print("Done.")
        return

    print("Fresh database detected — building schema from models...")

    # 1. Enable pgvector extension
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    print("  pgvector extension enabled.")

    # 2. Create all tables from current SQLAlchemy models
    Base.metadata.create_all(engine)
    print("  All tables created.")

    # 3. Stamp Alembic at head so future migrations apply correctly
    stamp_alembic_head(cfg)
    print("  Alembic stamped at head.")

    print("Database initialisation complete.")


if __name__ == "__main__":
    main()
