# Migrations Setup

## First Time Setup (Existing Database)

Since your database already has tables, initialize migrations with:

```bash
# Run ONCE to mark database at baseline
./scripts/init_migrations.sh
```

This tells Alembic "the database already has all tables" without creating them.

## Daily Workflow

After changing models:

```bash
# 1. Generate migration
./scripts/migrate.sh generate "Add user preferences"

# 2. Review generated file in migrations/versions/

# 3. Apply migration
./scripts/migrate.sh upgrade
```

## Commands

- `./scripts/migrate.sh check` - Check status and detect changes
- `./scripts/migrate.sh generate "msg"` - Create new migration
- `./scripts/migrate.sh upgrade` - Apply pending migrations
- `./scripts/migrate.sh downgrade` - Rollback last migration
- `./scripts/migrate.sh history` - View migration history

## Important Notes

- The baseline migration (001) is empty because tables already exist
- Only run `init_migrations.sh` ONCE per database
- Future migrations will only contain incremental changes
- Always review generated migrations before applying