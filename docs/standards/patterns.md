# Project Patterns

## Dependency Injection
Use constructor injection for all services and repositories. In FastAPI routes, use `Depends()`.

## Async/Await
Always use `async/await` for I/O operations (DB, AI APIs, Redis). Avoid blocking calls in the event loop.

## Future Feature Path
New backend features follow this path:

```text
FastAPI route -> command/query -> handler -> domain service/port -> infra adapter/repository
```

- API routes parse HTTP/auth/timezone/input and send commands or queries.
- Application handlers orchestrate use cases and own transaction timing through `AsyncUnitOfWork`.
- Domain code stays free of `src.api`, `src.app`, `src.infra`, SQLAlchemy, Redis, and HTTP clients.
- Repositories do not call `commit()` or `rollback()`; the UoW owns the transaction.
- Background work is awaited, supervised by `BackgroundTaskManager`, or moved to durable DB-backed state.
- Optional cache follows the selective cache admission policy; required transient state is not cache.

See `docs/architecture/async-cqrs-feature-alignment.md` for the full checklist.

## Error Handling
1. **Domain Exceptions**: Define custom exceptions in `src/domain/exceptions/` (e.g., `MealNotFoundError`).
2. **Logging**: Log at the point of origin with appropriate levels (`error`, `warning`, `info`).
3. **API Response**: Map domain exceptions to `HTTPException` in the API layer.

## File Size Limits
- **Services/Repos**: Max 400 lines. Split into sub-modules if exceeded.
- **Routes**: Group by feature, keep under 200 lines.
