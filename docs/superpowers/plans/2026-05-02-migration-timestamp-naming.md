# Migration Timestamp Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch new migration naming to YYYYMMDDHHMMSS format and add a CLI for generate/upgrade/downgrade/test/status commands.

**Architecture:** Update Alembic's file_template config, create a Python CLI that wraps Alembic commands with consistent logging, update the bash wrapper to delegate to the CLI.

**Tech Stack:** Python 3, Alembic, argparse, SQLAlchemy

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `alembic.ini` | Modify | Change file_template to timestamp format |
| `migrations/cli.py` | Create | Python CLI with generate/upgrade/downgrade/test/status commands |
| `scripts/development/migrate.sh` | Rewrite | Delegate all commands to Python CLI |
| `migrations/README.md` | Modify | Update documentation to match new workflow |

---

### Task 1: Update Alembic Configuration

**Files:**
- Modify: `alembic.ini:13`

- [ ] **Step 1: Update file_template in alembic.ini**

Change line 13 from:
```ini
file_template = %%(rev)s_%%(slug)s
```

To:
```ini
file_template = %%(year)d%%(month).2d%%(day).2d%%(hour).2d%%(minute).2d%%(second).2d_%%(slug)s
```

- [ ] **Step 2: Commit configuration change**

```bash
git add alembic.ini
git commit -m "chore: switch migration naming to YYYYMMDDHHMMSS format"
```

---

### Task 2: Create Migration CLI - Core Structure

**Files:**
- Create: `migrations/cli.py`

- [ ] **Step 1: Create cli.py with imports and logging setup**

```python
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
```

- [ ] **Step 2: Verify file is syntactically correct**

Run: `python -m py_compile migrations/cli.py`
Expected: No output (success)

- [ ] **Step 3: Commit core structure**

```bash
git add migrations/cli.py
git commit -m "feat(migrations): add CLI core structure"
```

---

### Task 3: Implement status Command

**Files:**
- Modify: `migrations/cli.py`

- [ ] **Step 1: Add cmd_status function before main()**

Add this function after `get_alembic_config()`:

```python
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
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile migrations/cli.py`
Expected: No output (success)

- [ ] **Step 3: Commit status command**

```bash
git add migrations/cli.py
git commit -m "feat(migrations): add status command to CLI"
```

---

### Task 4: Implement upgrade Command

**Files:**
- Modify: `migrations/cli.py`

- [ ] **Step 1: Add cmd_upgrade function after cmd_status()**

```python
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
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile migrations/cli.py`
Expected: No output (success)

- [ ] **Step 3: Commit upgrade command**

```bash
git add migrations/cli.py
git commit -m "feat(migrations): add upgrade command to CLI"
```

---

### Task 5: Implement downgrade Command

**Files:**
- Modify: `migrations/cli.py`

- [ ] **Step 1: Add cmd_downgrade function after cmd_upgrade()**

```python
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
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile migrations/cli.py`
Expected: No output (success)

- [ ] **Step 3: Commit downgrade command**

```bash
git add migrations/cli.py
git commit -m "feat(migrations): add downgrade command to CLI"
```

---

### Task 6: Implement generate Command

**Files:**
- Modify: `migrations/cli.py`

- [ ] **Step 1: Add cmd_generate function after cmd_downgrade()**

```python
def cmd_generate(args) -> int:
    """Generate new migration with autogenerate."""
    message = args.message.strip()

    if not message:
        logger.error("Migration message cannot be empty")
        return 1

    logger.info(f"Generating migration: {message}")

    try:
        alembic_cfg = get_alembic_config()

        # Generate migration with autogenerate
        command.revision(
            alembic_cfg,
            message=message,
            autogenerate=True,
        )

        logger.info("Migration generated successfully")
        logger.info("Review the generated file in migrations/versions/")
        return 0

    except Exception as e:
        logger.error(f"Failed to generate migration: {e}")
        return 1
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile migrations/cli.py`
Expected: No output (success)

- [ ] **Step 3: Commit generate command**

```bash
git add migrations/cli.py
git commit -m "feat(migrations): add generate command to CLI"
```

---

### Task 7: Implement test Command

**Files:**
- Modify: `migrations/cli.py`

- [ ] **Step 1: Add cmd_test function after cmd_generate()**

```python
def cmd_test(args) -> int:
    """Test migration cycle: upgrade -> downgrade -> upgrade."""
    logger.info("Testing migration cycle...")

    try:
        alembic_cfg = get_alembic_config()

        # Get initial state
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            initial_rev = context.get_current_revision()

        script_dir = ScriptDirectory.from_config(alembic_cfg)
        head_revision = script_dir.get_current_head()

        logger.info(f"Initial revision: {initial_rev or '<none>'}")
        logger.info(f"Head revision:    {head_revision or '<none>'}")

        # Step 1: Upgrade
        logger.info("Step 1/3: Upgrading...")
        command.upgrade(alembic_cfg, "head")

        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            after_upgrade = context.get_current_revision()
        logger.info(f"After upgrade: {after_upgrade}")

        # Step 2: Downgrade
        logger.info("Step 2/3: Downgrading...")
        command.downgrade(alembic_cfg, "-1")

        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            after_downgrade = context.get_current_revision()
        logger.info(f"After downgrade: {after_downgrade or '<none>'}")

        # Step 3: Upgrade again
        logger.info("Step 3/3: Upgrading again...")
        command.upgrade(alembic_cfg, "head")

        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            final_rev = context.get_current_revision()
        logger.info(f"Final revision: {final_rev}")

        if final_rev == head_revision:
            logger.info("Migration test PASSED")
            return 0
        else:
            logger.error(f"Migration test FAILED: expected {head_revision}, got {final_rev}")
            return 1

    except Exception as e:
        logger.error(f"Migration test FAILED: {e}")
        return 1
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile migrations/cli.py`
Expected: No output (success)

- [ ] **Step 3: Commit test command**

```bash
git add migrations/cli.py
git commit -m "feat(migrations): add test command to CLI"
```

---

### Task 8: Update Bash Wrapper

**Files:**
- Modify: `scripts/development/migrate.sh`

- [ ] **Step 1: Rewrite migrate.sh to delegate to Python CLI**

Replace entire contents with:

```bash
#!/bin/bash
#
# Migration CLI wrapper
#
# Usage:
#   ./scripts/development/migrate.sh generate "Add user preferences"
#   ./scripts/development/migrate.sh upgrade
#   ./scripts/development/migrate.sh downgrade
#   ./scripts/development/migrate.sh test
#   ./scripts/development/migrate.sh status

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Commands:"
    echo "  generate <message>  Generate new migration"
    echo "  upgrade             Apply pending migrations"
    echo "  downgrade           Rollback last migration"
    echo "  test                Test upgrade/downgrade cycle"
    echo "  status              Show migration status"
    exit 1
fi

python migrations/cli.py "$@"
```

- [ ] **Step 2: Verify script is executable**

Run: `chmod +x scripts/development/migrate.sh`

- [ ] **Step 3: Commit bash wrapper update**

```bash
git add scripts/development/migrate.sh
git commit -m "chore(migrations): update migrate.sh to use Python CLI"
```

---

### Task 9: Update Documentation

**Files:**
- Modify: `migrations/README.md`

- [ ] **Step 1: Update README.md with new workflow**

Replace entire contents with:

```markdown
# Migrations

Database migrations using Alembic with timestamp-based naming.

## Quick Start

```bash
# Check current status
./scripts/development/migrate.sh status

# Generate new migration after model changes
./scripts/development/migrate.sh generate "Add user preferences"

# Test migration locally (upgrade -> downgrade -> upgrade)
./scripts/development/migrate.sh test

# Apply migrations
./scripts/development/migrate.sh upgrade

# Rollback last migration
./scripts/development/migrate.sh downgrade
```

## Commands

| Command | Description |
|---------|-------------|
| `status` | Show current revision and pending migrations |
| `generate <msg>` | Create new migration with autogenerate |
| `upgrade` | Apply all pending migrations |
| `downgrade` | Rollback the last migration |
| `test` | Run upgrade -> downgrade -> upgrade cycle |

## Migration File Naming

New migrations use timestamp format: `YYYYMMDDHHMMSS_slug.py`

Example: `20260502143022_add_user_preferences.py`

Existing migrations (001-058) remain unchanged.

## First Time Setup

If this is a new database:

```bash
# Run ONCE to mark database at baseline
./scripts/init_migrations.sh
```

## Production Deployment

For production, use the deployment runner which includes retry logic:

```bash
python migrations/run.py
```

## Important Notes

- Always review generated migrations before applying
- Run `test` command locally before deploying
- The baseline migration (001) is empty because tables already existed
```

- [ ] **Step 2: Commit documentation update**

```bash
git add migrations/README.md
git commit -m "docs(migrations): update README with new CLI workflow"
```

---

### Task 10: Final Verification

**Files:**
- All modified files

- [ ] **Step 1: Verify all files exist**

Run:
```bash
ls -la alembic.ini migrations/cli.py scripts/development/migrate.sh migrations/README.md
```

Expected: All 4 files listed

- [ ] **Step 2: Verify CLI syntax is valid**

Run: `python -m py_compile migrations/cli.py`
Expected: No output (success)

- [ ] **Step 3: Verify CLI help works**

Run: `python migrations/cli.py --help`
Expected: Shows usage with all 5 commands listed

- [ ] **Step 4: Verify bash wrapper works**

Run: `./scripts/development/migrate.sh`
Expected: Shows usage with all 5 commands listed

- [ ] **Step 5: Create final commit if needed**

If any uncommitted changes remain:
```bash
git status
git add -A
git commit -m "chore(migrations): finalize CLI implementation"
```
