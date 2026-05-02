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
# Run ONCE to initialize the database
python scripts/init_postgres_db.py
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
