# Backend Troubleshooting Guide

**Last Updated:** May 6, 2026

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
3. Cache is optional — app continues without Redis (graceful degradation)

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
