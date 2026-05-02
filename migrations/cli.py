#!/usr/bin/env python
"""
Migration CLI for generating, testing, and applying database migrations.

Usage:
    python migrations/cli.py generate "Add user preferences"
    python migrations/cli.py upgrade
    python migrations/cli.py downgrade
    python migrations/cli.py test
    python migrations/cli.py status
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text

from migrations.utils import migration_engine as engine, MIGRATION_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ALEMBIC_CONFIG_PATH = "alembic.ini"


def get_alembic_config() -> Config:
    """Load Alembic configuration with database URL set."""
    config_path = Path(ALEMBIC_CONFIG_PATH)
    if not config_path.exists():
        logger.error(f"Alembic config not found: {config_path.absolute()}")
        sys.exit(1)

    alembic_cfg = Config(str(config_path))
    alembic_cfg.set_main_option("sqlalchemy.url", MIGRATION_URL)
    return alembic_cfg


def cmd_generate(args) -> int:
    """Placeholder - implemented in Task 3."""
    raise NotImplementedError("cmd_generate")


def cmd_upgrade(args) -> int:
    """Apply pending migrations."""
    logger.info("Upgrading database...")

    try:
        alembic_cfg = get_alembic_config()

        # Show current state
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            before_rev = context.get_current_revision()

        logger.info(f"Current revision: {before_rev or '<none>'}")

        # Run upgrade
        command.upgrade(alembic_cfg, "head")

        # Show new state
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            after_rev = context.get_current_revision()

        if before_rev == after_rev:
            logger.info("No pending migrations")
        else:
            logger.info(f"Upgraded to: {after_rev}")

        logger.info("Upgrade completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Upgrade failed: {e}")
        return 1


def cmd_downgrade(args) -> int:
    """Rollback last migration."""
    logger.info("Downgrading database...")

    try:
        alembic_cfg = get_alembic_config()

        # Show current state
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            before_rev = context.get_current_revision()

        if before_rev is None:
            logger.info("No migrations to rollback")
            return 0

        logger.info(f"Current revision: {before_rev}")

        # Run downgrade by one step
        command.downgrade(alembic_cfg, "-1")

        # Show new state
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            after_rev = context.get_current_revision()

        logger.info(f"Downgraded to: {after_rev or '<none>'}")
        logger.info("Downgrade completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Downgrade failed: {e}")
        return 1


def cmd_test(args) -> int:
    """Placeholder - implemented in Task 6."""
    raise NotImplementedError("cmd_test")


def cmd_status(args) -> int:
    """Show current migration status."""
    logger.info("Checking migration status...")

    try:
        alembic_cfg = get_alembic_config()
        script_dir = ScriptDirectory.from_config(alembic_cfg)

        # Get head revision
        head_revision = script_dir.get_current_head()

        # Get current revision from database
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_revision = context.get_current_revision()

        logger.info(f"Current revision: {current_revision or '<none>'}")
        logger.info(f"Head revision:    {head_revision or '<none>'}")

        if current_revision == head_revision:
            logger.info("Database is up to date")
        elif current_revision is None:
            logger.info("Database has no migrations applied")
        else:
            # Count pending migrations
            revisions = list(script_dir.walk_revisions(head_revision, current_revision))
            pending_count = len(revisions) - 1  # Exclude current
            logger.info(f"Pending migrations: {pending_count}")

        return 0

    except Exception as e:
        logger.error(f"Failed to check status: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Migration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate new migration")
    gen_parser.add_argument("message", help="Migration message")
    gen_parser.set_defaults(func=cmd_generate)

    # upgrade
    up_parser = subparsers.add_parser("upgrade", help="Apply pending migrations")
    up_parser.set_defaults(func=cmd_upgrade)

    # downgrade
    down_parser = subparsers.add_parser("downgrade", help="Rollback last migration")
    down_parser.set_defaults(func=cmd_downgrade)

    # test
    test_parser = subparsers.add_parser("test", help="Test upgrade/downgrade cycle")
    test_parser.set_defaults(func=cmd_test)

    # status
    status_parser = subparsers.add_parser("status", help="Show migration status")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
