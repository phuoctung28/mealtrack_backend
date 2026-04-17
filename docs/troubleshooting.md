# Backend Troubleshooting Guide

**Last Updated:** April 17, 2026

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

**Prevention:** Run type checker before commit:
```bash
mypy src/
```

---

### Database Connection Errors

**Problem:** `OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server..."`

**Diagnosis:**
```bash
# Check DATABASE_URL format
echo $DATABASE_URL
# Should be: mysql+pymysql://user:pass@host:3306/dbname
```

**Solutions:**
1. Verify MySQL is running
2. Check `DATABASE_URL` format (user, pass, host, port, dbname)
3. Verify credentials and network access
4. Check firewall rules

**Prevention:** Test connection on startup:
```bash
# In settings.py
if not test_db_connection():
    raise RuntimeError("Database connection failed")
```

---

### Migration Conflicts

**Problem:** `alembic upgrade head` fails with "heads are not equal"

**Diagnosis:**
```bash
alembic heads
# Shows multiple head revisions
```

**Solutions:**
1. List all heads: `alembic heads`
2. Merge conflicts manually or use merge command:
   ```bash
   alembic merge -m "Merge heads"
   ```
3. Resolve conflicts in merged migration file
4. Apply: `alembic upgrade head`

**Prevention:**
- Pull before creating new migrations
- Use feature branches for parallel work
- Review migration conflicts in code review

---

### Authentication Failures

**Problem:** `AuthenticationException` or JWT verification fails

**Diagnosis:**
```bash
# Check Firebase credentials file
ls -la $FIREBASE_CREDENTIALS
cat $FIREBASE_CREDENTIALS | head -5

# Test token verification
python -c "from src.api.dependencies.auth import verify_firebase_token; verify_firebase_token('test-token')"
```

**Solutions:**
1. Verify Firebase credentials file path and content
2. Check Firebase project ID matches
3. Verify token is valid JWT format
4. Check token expiration (use `jwt.decode(..., options={"verify_exp": False})`)
5. In dev, use `dev_auth_bypass_middleware` (enabled by `DEV_MODE=true`)

**Prevention:**
- Test Firebase SDK initialization on app startup
- Log token verification errors (redact token)
- Use dev bypass for local development

---

### Type Errors

**Problem:** `error: Argument 1 to "X" has incompatible type` from mypy

**Diagnosis:**
```bash
mypy src/ --show-column-numbers --show-error-codes
```

**Solutions:**
1. Add type hints to function signature
2. Use `Optional[T]` for nullable values
3. Use `Union[T1, T2]` for multiple types
4. Check if using `Any` (too permissive)

**Prevention:** Run before commit:
```bash
mypy src/ && black src/ && flake8 src/
```

---

### Redis Connection Issues

**Problem:** `ConnectionError` or Redis not available

**Diagnosis:**
```bash
redis-cli ping
# Should return: PONG

# Check REDIS_URL
echo $REDIS_URL
# Should be: redis://host:port/db
```

**Solutions:**
1. Verify Redis is running
2. Check `REDIS_URL` format (host, port, db number)
3. Verify firewall/network access
4. Cache is optional: app continues without Redis (graceful degradation)

**Prevention:**
- Test Redis connection on startup
- Log cache errors but don't fail the request
- Monitor cache hit rates in Sentry

---

### Slow Database Queries

**Problem:** `[SLOW_REQUEST_DETECTED >1s]` in logs

**Diagnosis:**
```bash
# Enable query logging
SQLALCHEMY_ECHO=true python src/api/main.py

# Check slow logs
mysql> SET GLOBAL slow_query_log='ON';
mysql> SET GLOBAL long_query_time=1;
```

**Solutions:**
1. Add indexes on frequently filtered columns
2. Use eager loading (joinedload) instead of lazy loading
3. Check N+1 queries: is one query spawning many?
4. Profile with `explain()`:
   ```python
   from sqlalchemy import text
   result = session.execute(text("EXPLAIN ANALYZE SELECT ..."))
   ```
5. Consider caching (Redis) for frequently read data

**Prevention:**
- Monitor request durations in logs
- Set slow query alerts in Sentry
- Profile critical paths in tests

---

### Event Bus Handler Not Called

**Problem:** Command/query dispatched but handler not invoked

**Diagnosis:**
```bash
# Check handler is registered
grep -r "@handles" src/app/handlers/

# Check event_bus initialization
python -c "from src.infra.event_bus import get_event_bus; bus = get_event_bus(); print(bus._handlers.keys())"
```

**Solutions:**
1. Verify `@handles` decorator on handler class
2. Check handler is imported in `src/infra/event_bus/` init
3. Verify command/query class name matches exactly
4. Check handler `async def handle()` signature
5. Ensure event bus is singleton (not recreated per request)

**Prevention:**
- Add unit tests for all handlers
- Log handler registration on startup
- Use type hints to catch mismatches

---

### External Service Timeouts

**Problem:** Gemini/Cloudinary/Firebase requests timeout

**Diagnosis:**
```bash
# Check timeout settings
grep -r "timeout" src/infra/services/

# Monitor latency in Sentry
# Check service status pages
```

**Solutions:**
1. Increase timeout (but don't exceed 30s for FastAPI)
2. Implement retry logic with exponential backoff
3. Cache responses when possible
4. Use request-level timeout handling
5. Add circuit breaker for repeated failures

**Prevention:**
- Set reasonable timeouts (10-30s based on service)
- Implement graceful degradation
- Monitor P95/P99 latencies in Sentry
- Add alerts for service degradation

---

### File Size Limit Exceeded

**Problem:** `FileTooLargeError` when uploading meal image

**Diagnosis:**
```bash
# Check file size limit
grep -r "MAX_FILE_SIZE\|10.*1024\*1024" src/

# Check actual file size
ls -lh /path/to/image
```

**Solutions:**
1. Reduce image size before upload (client-side)
2. Increase limit if needed (default 10MB)
3. Compress image on upload
4. Add client-side validation

**Prevention:**
- Document max file size in API docs
- Provide clear error message to client
- Move limit to config (not hardcoded)

---

### CORS Errors

**Problem:** Browser blocks cross-origin requests

**Diagnosis:**
```bash
# Check CORS headers in response
curl -i -X OPTIONS "http://localhost:8000/v1/meals"

# Check CORS config
grep -r "allow_origins\|CORS" src/api/
```

**Solutions:**
1. In development: `allow_origins=["*"]` (already set)
2. In production: Restrict to known origins
3. Add `allow_credentials=True` if needed
4. Verify preflight request (OPTIONS) returns 200

**Prevention:**
- Use environment-based CORS config
- Document allowed origins
- Test with real client origins

---

## Testing & Debugging

**Run tests with output:**
```bash
pytest -v -s tests/unit/domain/services/test_meal_service.py
```

**Run specific test:**
```bash
pytest -k "test_tdee_calculation_with_body_fat" -v
```

**Debug with breakpoint:**
```python
import pdb; pdb.set_trace()
```

**Profile memory:**
```bash
pip install memory_profiler
python -m memory_profiler src/api/main.py
```

---

## Getting Help

1. **Check logs:** `tail -f logs/app.log`
2. **Check Sentry:** https://sentry.io/organizations/...
3. **Run tests:** `pytest -v` to isolate issue
4. **Ask team:** Post in #backend Slack channel with error + context
5. **Check docs:** `docs/` folder for architecture/patterns

---

See related: `code-standards.md`, `testing-standards.md`, `system-architecture.md`
