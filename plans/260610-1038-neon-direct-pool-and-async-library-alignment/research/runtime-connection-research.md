---
type: research
topic: neon direct pool and asyncpg connection policy
created: "2026-06-10"
---

# Runtime Connection Research

## Summary

The platform should make DB connection mode explicit. For this backend, the
preferred production runtime is direct Neon URL plus SQLAlchemy async app pool.
Neon pooler remains a supported fallback only when configured for asyncpg and
PgBouncer transaction mode.

## Current Code Findings

- `src/infra/database/config_async.py` normalizes PostgreSQL URLs to asyncpg.
- Current app runtime picks `DATABASE_URL_DIRECT` before `DATABASE_URL`.
- Current pool behavior defaults to `NullPool`; queue pooling requires
  `ASYNC_DB_USE_QUEUE_POOL=true`.
- `.env.example` still tells app traffic to use Neon pooler in `DATABASE_URL`.
- Code reads `ASYNC_POOL_SIZE_PER_WORKER`, but `.env.example` shows
  `POOL_SIZE_PER_WORKER`.
- Migrations use `migrations/utils.py`, direct URL, sync SQLAlchemy engine, and
  `psycopg2`; keep this path for now.

## External Reference Findings

- Neon recommends pooled connections for high-concurrency web/serverless
  workloads, and direct connections for migrations/admin/session-sensitive work.
- Neon pooler is PgBouncer transaction mode. SQL-level `PREPARE`/`DEALLOCATE`,
  session advisory locks, persistent `SET`, and similar session features are not
  supported.
- Neon PgBouncer supports protocol-level prepared statements, but this still
  relies on driver compatibility.
- SQLAlchemy asyncpg uses prepared statements and caches them by default. It
  documents `prepared_statement_cache_size=0` and PgBouncer-specific prepared
  statement naming guidance.
- asyncpg FAQ explicitly flags PgBouncer transaction/statement mode as the
  common cause of intermittent prepared statement errors.

## Design Conclusion

Use:

```text
DB_CONNECTION_MODE=direct_pool
APP_DATABASE_URL=<direct Neon URL>
ASYNC_DB_USE_QUEUE_POOL=true
```

Keep:

```text
DATABASE_URL_DIRECT or MIGRATION_DATABASE_URL=<direct Neon URL>
```

Use pooler mode only when:

- connection count is the bottleneck,
- transactions are short,
- session-level DB features are not needed,
- prepared-statement cache safeguards are enabled.

## Open Questions

- Confirm actual Neon compute size and production Render worker count during
  implementation to set safe default pool size.
