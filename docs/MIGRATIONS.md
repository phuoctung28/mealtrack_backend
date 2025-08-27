# Database Migrations Guide

## Setup (For Existing Database)

Since your database already has tables created by `Base.metadata.create_all()`, you need to initialize Alembic:

```bash
# Tell Alembic your database is at the baseline (DO NOT use 'upgrade')
.venv/bin/alembic stamp 001
```

This marks your database as being at revision 001 without running any SQL.

## Overview

This project uses Alembic for database schema migrations to track future changes to your SQLAlchemy models.

## Quick Start

After making changes to SQLAlchemy models:

```bash
# 1. Check current status and detect changes
./scripts/migrate.sh check

# 2. Generate a new migration
./scripts/migrate.sh generate "Add user preferences table"

# 3. Review the generated migration file in migrations/versions/

# 4. Apply the migration locally to test
./scripts/migrate.sh upgrade

# 5. Commit both your model changes and the migration file
git add src/infra/database/models/ migrations/versions/
git commit -m "Add user preferences table with migration"
```

## Commands

### Check Status
```bash
./scripts/migrate.sh check
```
Shows current database revision, available migrations, and detects model changes.

### Generate Migration
```bash
./scripts/migrate.sh generate "description of changes"
```
Creates a new migration file based on model changes. **Always review the generated file!**

### Apply Migrations
```bash
./scripts/migrate.sh upgrade
```
Applies all pending migrations to bring database to latest version.

### Rollback Migration
```bash
./scripts/migrate.sh downgrade -1  # Roll back one migration
./scripts/migrate.sh downgrade <revision>  # Roll back to specific revision
```

### View History
```bash
./scripts/migrate.sh history
```
Shows all migrations and their relationships.

## Best Practices

### ✅ DO:

1. **Always generate migrations after model changes**
   - Don't commit model changes without corresponding migrations
   - This ensures database schema stays in sync with code

2. **Review auto-generated migrations carefully**
   - Alembic may not detect all changes correctly
   - Check for data loss operations (column drops, type changes)
   - Verify foreign key constraints are correct

3. **Test migrations locally before committing**
   - Run `./scripts/migrate.sh upgrade` to verify it works
   - Test rollback with `./scripts/migrate.sh downgrade -1`

4. **Write descriptive migration messages**
   ```bash
   # Good
   ./scripts/migrate.sh generate "Add indexes to user_meals for performance"
   
   # Bad
   ./scripts/migrate.sh generate "fix"
   ```

5. **Keep migrations small and focused**
   - One logical change per migration
   - Easier to review, test, and rollback if needed

### ❌ DON'T:

1. **Don't edit applied migrations**
   - Once a migration is committed and applied in production, never edit it
   - Create a new migration to fix issues

2. **Always review auto-generated migrations**
   - Migrations need careful review
   - Auto-generation can miss complex changes
   - May create unintended data loss operations

3. **Don't skip migration generation**
   - Even "small" model changes need migrations
   - Forgetting migrations causes deployment failures

4. **Don't manually edit the alembic_version table**
   - Use Alembic commands to manage migration state

## Common Scenarios

### Adding a New Column
```python
# In your model
class User(Base):
    # ... existing fields ...
    preferences = Column(JSON, nullable=True)  # New field
```
```bash
./scripts/migrate.sh generate "Add preferences column to users table"
```

### Creating a New Table
```python
# New model file
class UserPreference(Base):
    __tablename__ = 'user_preferences'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    # ... other fields ...
```
```bash
./scripts/migrate.sh generate "Create user_preferences table"
```

### Adding an Index
```python
class Meal(Base):
    __tablename__ = 'meals'
    # ... fields ...
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'consumed_at'),  # New index
    )
```
```bash
./scripts/migrate.sh generate "Add composite index on meals for user queries"
```

## Troubleshooting

### "Multiple heads" error
This happens when branches have conflicting migrations:
```bash
# Create a merge migration
.venv/bin/alembic merge -m "Merge migrations from feature branches"
```

### "Can't locate revision" error
Database is out of sync with migration files:
```bash
# Check current state
.venv/bin/alembic current

# Force to specific revision (use carefully!)
.venv/bin/alembic stamp <revision>
```

### Auto-generate missed changes
Some changes aren't detected automatically:
- Column renames (seen as drop + add)
- Table renames
- Some constraint changes

For these, manually edit the generated migration file.

## Deployment
```bash
# For existing databases (first time):
.venv/bin/alembic stamp 001

# For future deployments (after new migrations):
.venv/bin/alembic upgrade head
```

## Helper Scripts

### Model Change Detection
The `scripts/check_migrations.py` script helps detect model changes:

```bash
# Just check for changes
python scripts/check_migrations.py --check-only

# Reset the change detection hash
python scripts/check_migrations.py --force
```

This is useful for:
- CI checks to ensure migrations aren't forgotten
- Local development to quickly see if models changed
- Resetting after manual migration edits