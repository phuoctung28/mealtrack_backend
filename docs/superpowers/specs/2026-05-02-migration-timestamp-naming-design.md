# Migration Timestamp Naming Design

**Date:** 2026-05-02  
**Status:** Approved

## Overview

Switch migration file naming from sequential numbers (001, 002, ...) to timestamp-based format (YYYYMMDDHHMMSS) for new migrations only. Add a proper CLI for generating and testing migrations locally.

## Goals

1. Avoid merge conflicts when multiple developers create migrations simultaneously
2. Provide clear commands for generating, testing, and applying migrations
3. Enable local upgrade/downgrade testing before deployment

## Non-Goals

- Renaming existing 58 migrations (001-058 remain as-is)
- Changing Alembic's internal revision tracking

## Design

### 1. Alembic Configuration

Update `alembic.ini`:

```ini
# Before
file_template = %%(rev)s_%%(slug)s

# After
file_template = %%(year)d%%(month).2d%%(day).2d%%(hour).2d%%(minute).2d%%(second).2d_%%(slug)s
```

Example output: `20260502143022_add_user_preferences.py`

### 2. Python Migration CLI

Create `migrations/cli.py` with commands:

| Command | Description |
|---------|-------------|
| `generate <message>` | Create new migration with autogenerate |
| `upgrade` | Apply pending migrations |
| `downgrade` | Rollback last migration |
| `test` | Run upgrade -> downgrade -> upgrade cycle |
| `status` | Show current revision and pending migrations |

#### Implementation Details

- Reuse `migrations/utils.py` for database connection (migration_engine)
- Reuse logging patterns from `migrations/run.py`
- `generate` requires a non-empty message, slugifies for filename
- `test` command runs: upgrade → downgrade → upgrade. If any step fails, stop immediately and report which step failed. Exit 0 on success, exit 1 on failure.
- All commands provide clear success/failure output

#### CLI Structure

```python
# migrations/cli.py
import argparse
from alembic import command
from alembic.config import Config

def cmd_generate(args):
    """Generate new migration with autogenerate."""
    
def cmd_upgrade(args):
    """Apply pending migrations."""
    
def cmd_downgrade(args):
    """Rollback last migration."""
    
def cmd_test(args):
    """Test migration cycle: upgrade -> downgrade -> upgrade."""
    
def cmd_status(args):
    """Show current migration status."""

def main():
    parser = argparse.ArgumentParser(description="Migration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # generate
    gen_parser = subparsers.add_parser("generate")
    gen_parser.add_argument("message", help="Migration message")
    gen_parser.set_defaults(func=cmd_generate)
    
    # upgrade
    up_parser = subparsers.add_parser("upgrade")
    up_parser.set_defaults(func=cmd_upgrade)
    
    # downgrade
    down_parser = subparsers.add_parser("downgrade")
    down_parser.set_defaults(func=cmd_downgrade)
    
    # test
    test_parser = subparsers.add_parser("test")
    test_parser.set_defaults(func=cmd_test)
    
    # status
    status_parser = subparsers.add_parser("status")
    status_parser.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    args.func(args)
```

### 3. Bash Wrapper Update

Update `scripts/development/migrate.sh` to delegate to Python CLI:

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"
python migrations/cli.py "$@"
```

Usage:
```bash
./scripts/development/migrate.sh generate "Add user preferences"
./scripts/development/migrate.sh upgrade
./scripts/development/migrate.sh downgrade
./scripts/development/migrate.sh test
./scripts/development/migrate.sh status
```

### 4. Documentation Update

Update `migrations/README.md` to reflect new workflow:

```markdown
## Daily Workflow

# Generate new migration
./scripts/development/migrate.sh generate "Add user preferences"

# Review generated file in migrations/versions/

# Test locally (upgrade -> downgrade -> upgrade)
./scripts/development/migrate.sh test

# Apply migration
./scripts/development/migrate.sh upgrade
```

## Files Changed

| File | Change |
|------|--------|
| `alembic.ini` | Update file_template to timestamp format |
| `migrations/cli.py` | New file - Python CLI |
| `scripts/development/migrate.sh` | Rewrite to delegate to CLI |
| `migrations/README.md` | Update documentation |

## Migration Path

1. Update `alembic.ini` - immediate effect on new migrations
2. Add `migrations/cli.py` - new CLI available
3. Update `migrate.sh` - existing scripts start using new CLI
4. Update README - docs match reality

No changes to existing migrations. No database changes required.

## Testing Plan

1. Generate a test migration, verify timestamp naming
2. Run `test` command, verify upgrade/downgrade cycle works
3. Delete test migration
4. Verify existing migrations still apply correctly
