# Project Patterns

## Dependency Injection
Use constructor injection for all services and repositories. In FastAPI routes, use `Depends()`.

## Async/Await
Always use `async/await` for I/O operations (DB, AI APIs, Redis). Avoid blocking calls in the event loop.

## Error Handling
1. **Domain Exceptions**: Define custom exceptions in `src/domain/exceptions/` (e.g., `MealNotFoundError`).
2. **Logging**: Log at the point of origin with appropriate levels (`error`, `warning`, `info`).
3. **API Response**: Map domain exceptions to `HTTPException` in the API layer.

## File Size Limits
- **Services/Repos**: Max 400 lines. Split into sub-modules if exceeded.
- **Routes**: Group by feature, keep under 200 lines.
