# Backend Troubleshooting Guide

**Last Updated:** June 13, 2026

---

## Common Issues

### Import Errors

**Problem:** `ModuleNotFoundError` or circular imports

**Diagnosis:**
```bash
python -c "from src.app.commands.meal import CreateMealCommand"
```

**Solutions:**
1. Check `__init__.py` exports in package
2. Verify relative imports use `.` notation
3. Check for circular dependencies: A imports B imports A

---

### Database Connection Errors

**Problem:** `OperationalError: Can't connect to MySQL server`

**Diagnosis:**
```bash
echo $DATABASE_URL
# Should be: mysql+pymysql://user:pass@host:3306/dbname
```

**Solutions:**
1. Verify `DATABASE_URL` format (user, pass, host, port, dbname)
2. Verify MySQL is running and credentials are correct
3. Check firewall/network access rules

---

### Migration Conflicts

**Problem:** `alembic upgrade head` fails with "heads are not equal"

**Solutions:**
1. `alembic heads` — list all head revisions
2. Merge: `alembic merge -m "Merge heads"`
3. Resolve conflicts in merged migration file, then `alembic upgrade head`

**Prevention:** Pull before creating new migrations; use feature branches.

---

### Authentication Failures

**Problem:** `AuthenticationException` or JWT verification fails

**Diagnosis:**
```bash
ls -la $FIREBASE_CREDENTIALS
```

**Solutions:**
1. Verify Firebase credentials file path and content
2. Check Firebase project ID matches environment
3. Verify token is valid and not expired
4. In dev: use `DEV_MODE=true` to enable `X-Dev-User-Id` header bypass

---

### Redis Connection Issues

**Problem:** `ConnectionError` or Redis not available

**Diagnosis:**
```bash
redis-cli ping
# Should return: PONG
```

**Solutions:**
1. Check `REDIS_URL` format: `redis://host:port/db`
2. Verify Redis is running
3. Optional caches are bypassed when Redis is unavailable. Features that explicitly require Redis-backed state must fail fast or use a durable store.

---

### Slow Database Queries

**Problem:** `[SLOW_REQUEST_DETECTED >1s]` in logs

**Diagnosis:**
```bash
SQLALCHEMY_ECHO=true python src/api/main.py
```

**Solutions:**
1. Add indexes on frequently filtered columns
2. Use `joinedload` to avoid N+1 queries
3. Profile with `EXPLAIN ANALYZE` via SQLAlchemy `text()`
4. Consider Redis caching for frequently read data

---

### Event Bus Handler Not Called

**Problem:** Command/query dispatched but handler not invoked

**Diagnosis:**
```bash
grep -r "@handles" src/app/handlers/
```

**Solutions:**
1. Verify `@handles` decorator on handler class
2. Check handler is imported in the event bus init
3. Verify command/query class name matches exactly
4. Ensure event bus is singleton (not recreated per request)

---

### External Service Timeouts

**Problem:** Gemini/Cloudinary/Firebase requests timeout

**Solutions:**
1. Increase timeout (max 30s for FastAPI)
2. Implement retry logic with exponential backoff
3. Cache responses where possible
4. Add circuit breaker for repeated failures

---

### Sentry Events Missing

**Problem:** Expected production errors do not appear in Sentry

**Diagnosis:**
```bash
echo $SENTRY_DSN
rg "import sentry_sdk|sentry_sdk\\." src
```

**Solutions:**
1. Verify `SENTRY_DSN` is set in the runtime environment.
2. Verify startup calls `initialize_observability()` before `FastAPI(...)`.
3. Keep direct SDK usage isolated to `src/infra/monitoring/sentry.py`; cron and service code should call the facade.
4. For swallowed cron failures, call `capture_exception(...)` and `flush_observability(timeout=5)` before process exit.
5. Do not attach raw request bodies, auth headers, Firebase claims, emails, food payloads, raw image URLs, provider payloads, or secrets.

### Sentry Logs or Metrics Missing

**Problem:** Sentry error events appear, but Sentry Logs or application metrics are missing.

**Diagnosis:**
```bash
echo $SENTRY_ENABLE_LOGS
echo $SENTRY_ENABLE_METRICS
rg "log_event|increment_metric|gauge_metric|distribution_metric" src
```

**Solutions:**
1. Set `SENTRY_ENABLE_LOGS=true` for Sentry Logs ingestion.
2. Set `SENTRY_ENABLE_METRICS=true` for application metric ingestion.
3. Emit structured logs and metrics through `src.infra.monitoring`; Python `logging.info(...)` is not the same as a Sentry Logs facade call.
4. Keep attributes allowlisted and scalar. Non-allowlisted, `None`, list, and dict attributes are dropped before reaching Sentry.

---

### CORS Errors

**Problem:** Browser blocks cross-origin requests

**Diagnosis:**
```bash
curl -i -X OPTIONS "http://localhost:8000/v1/meals"
```

**Solutions:**
1. Development: `allow_origins=["*"]` (already set)
2. Production: Restrict to known origins via environment config
3. Verify preflight (OPTIONS) returns 200

---

## Testing & Debugging

```bash
# Run specific test with output
pytest -v -s tests/unit/domain/services/test_meal_service.py

# Run by name pattern
pytest -k "test_tdee_calculation_with_body_fat" -v

# Debug breakpoint
import pdb; pdb.set_trace()
```

---

See related: `code-standards.md`, `testing-standards.md`, `system-architecture.md`

---

## Database Connection Issues

### asyncpg prepared statement error in pooler mode
**Symptom:** `asyncpg.exceptions.InvalidSQLStatementNameError: prepared statement ... does not exist`  
**Cause:** Using a Neon `-pooler` URL without `DB_CONNECTION_MODE=neon_pooler`. PgBouncer transaction mode invalidates prepared statements between connections.  
**Fix:** Set `DB_CONNECTION_MODE=neon_pooler` and ensure `APP_DATABASE_URL` points to a `-pooler` endpoint.

### direct_pool startup error: pooler URL rejected
**Symptom:** `ConnectionPolicyError: DB_CONNECTION_MODE=direct_pool requires a direct (non-pooler) Neon URL`  
**Cause:** `APP_DATABASE_URL` contains `-pooler` in the hostname but mode is `direct_pool`.  
**Fix:** Either change `APP_DATABASE_URL` to a direct endpoint, or set `DB_CONNECTION_MODE=neon_pooler`.

### DB connection exhaustion (direct_pool)
**Symptom:** Connection timeouts, Neon `max_connections` limit hit.  
**Fix:** Reduce pool size: lower `ASYNC_POOL_SIZE_PER_WORKER` or `UVICORN_WORKERS`. Monitor `/v1/health/db-pool` for utilization. Consider switching to `neon_pooler` mode.

### Migration fails but app works (or vice versa)
**Symptom:** `alembic upgrade head` fails / succeeds independently of the app.  
**Cause:** `DATABASE_URL_DIRECT` (migration URL) and `APP_DATABASE_URL` (app URL) can differ.  
**Fix:** Ensure `DATABASE_URL_DIRECT` points to the direct Neon endpoint for migrations.
