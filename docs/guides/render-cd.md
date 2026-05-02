# Render CD Flow

## Production Flow

Render should run database migrations before starting the new web service:

1. Build Docker image.
2. Run pre-deploy command.
3. Start web service only if pre-deploy succeeds.
4. Health check `/health`.

## Render Settings

Production service:

```text
Branch: main
Runtime: Docker
Pre-deploy command: python migrations/run.py
Docker command: /app/docker-entrypoint.sh
Health check path: /health
```

Staging service:

```text
Branch: delivery
Runtime: Docker
Pre-deploy command: python migrations/run.py
Docker command: /app/docker-entrypoint.sh
Health check path: /health
```

## Environment Variables

Use these deployment-related variables:

```text
WEB_CONCURRENCY=1
MIGRATION_LOCK_TIMEOUT_MS=10000
MIGRATION_STATEMENT_TIMEOUT_MS=240000
```

`docker-entrypoint.sh` intentionally does not run migrations. Do not add migration
commands back to container startup.

## Why

Migrations in startup can make the web container fail to bind to Render's port.
Render then restarts the container and repeats the migration attempt. Running
migrations as a pre-deploy command fails the deploy before promotion and keeps
the previous healthy service running.

## Emergency Recovery

If a migration is blocking production startup:

1. Temporarily set pre-deploy command to:

```bash
echo "Skipping migrations for prod recovery"
```

2. Deploy the current production branch.
3. Fix Alembic/database state.
4. Restore pre-deploy command:

```bash
python migrations/run.py
```

Do not downgrade production schema during an incident unless the migration is
known to be destructive and data ownership has been reviewed.
