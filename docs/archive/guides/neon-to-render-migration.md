# Neon → Render PostgreSQL Migration

## Why

Render Basic plan: **$9/month, 10GB storage, 256MB RAM**
Neon Launch plan: **$19/month, 10GB storage**

Same storage, half the price. Trade-off: lose Neon's serverless branching (not used in production).

## Prerequisites

- `pg_dump` and `pg_restore` installed locally (`brew install libpq`)
- Render PostgreSQL instance provisioned (Basic plan, $9/mo)
- Connection strings for both databases ready

## Step 1: Verify pgvector on Render

Connect to Render DB and confirm pgvector is available before doing anything else:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

If this errors, stop — pgvector is required for `meal_image_cache`.

## Step 2: Dump from Neon

```bash
pg_dump "postgresql://USER:PASSWORD@NEON_HOST/dbname" \
  --no-owner --no-acl -Fc -f neon_backup.dump
```

Expected: completes in under a minute (database is ~10MB).

## Step 3: Restore to Render

```bash
pg_restore \
  --no-owner --no-acl \
  -d "postgresql://USER:PASSWORD@RENDER_HOST/dbname" \
  neon_backup.dump
```

## Step 4: Verify restore

```sql
-- Run on Render — should match Neon row counts
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Step 5: Update environment variables

Replace `DATABASE_URL` everywhere:

- `.env` (local dev)
- Production environment variables (wherever the backend is deployed)
- GitHub Actions secrets if any workflows use `DATABASE_URL`

```bash
# New value format
DATABASE_URL=postgresql://USER:PASSWORD@RENDER_HOST/dbname
```

## Step 6: Run migrations

Confirm schema is up to date on Render:

```bash
alembic upgrade head
```

Should output `INFO  [alembic.runtime.migration] Running upgrade ... -> ...` or no-op if restore already included latest schema.

## Step 7: Smoke test

Start the backend locally pointing at Render DB and hit a few endpoints:

```bash
# Quick health check
curl http://localhost:8000/health

# Test a DB-hitting endpoint
curl -H "Authorization: Bearer ..." http://localhost:8000/v1/meals
```

## Step 8: Cut over

Once verified:

1. Deploy backend with new `DATABASE_URL`
2. Monitor logs for any connection errors
3. Cancel Neon subscription after 1-2 days of stable prod traffic

## Rollback

If anything goes wrong, revert `DATABASE_URL` to the Neon connection string. Neon data is untouched throughout this process — pg_dump is read-only.

---

**Current DB size:** ~10MB (as of April 2026)
**Estimated migration time:** < 5 minutes
