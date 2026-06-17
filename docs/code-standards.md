# Backend Code Standards — Python Style & Conventions

**Last Updated:** June 17, 2026
**Scope:** All code in `src/` (620 Python files, ~52.6K LOC)
**Applies To:** Typing, naming, imports, code organization, error handling

---

## File Naming Conventions

### All Files
- Use `snake_case.py` for all Python files
- Descriptive names (prefer longer, clearer names over abbreviations)

### Pattern-Based Naming
| Pattern | Example | Purpose |
|---------|---------|---------|
| `*_command.py` | `create_meal_command.py` | Write operations |
| `*_query.py` | `get_meal_by_id_query.py` | Read operations |
| `*_event.py` | `meal_created_event.py` | Domain events |
| `*_handler.py` | `create_meal_command_handler.py` | CQRS handlers |
| `*_service.py` | `tdee_service.py` | Domain/app services |
| `*_repository.py` | `meal_repository.py` | Data access |
| `*_port.py` | `meal_repository_port.py` | Port interfaces |

---

## File Size Limits (200-Line Principle)

Keep files small enough to read, review, and — for AI-context files — load with full model attention. Origin: context-engineering research on LLM instruction-following (degradation past ~200–300 instructions). Source: [Quy tắc 200 dòng](https://thieunv.substack.com/p/ce-02-quy-tac-200-dong).

### Code files
- **Target**: <200 LOC per file for readability
- **Maximum**: 400 LOC absolute limit
- **Action**: Split into smaller, focused modules if exceeding target

### Documentation & AI-context files
Entry points stay lean; detail moves to on-demand references (progressive disclosure):
- **`CLAUDE.md`**: <100 lines (loads every session)
- **Tier-3 reference docs** (`docs/*.md`): target <200 lines, hard cap ~300; split by topic and link from the entry point
- Treat each doc as a table of contents that points to detail, not a dumping ground

---

## Type Hints (Required)

**All function signatures must have type hints:**

```python
def calculate_tdee(
    request: TdeeRequest,
    formula: Optional[str] = None,
) -> TdeeResponse:
    pass
```

---

## Dataclasses

Prefer dataclasses for DTOs and value objects:

```python
@dataclass
class Nutrition:
    calories: float
    protein: float
    carbs: float
    fat: float
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.calories < 0:
            raise ValueError("Calories cannot be negative")
```

---

## Enums

Use enums for constrained values:

```python
class MealStatus(str, Enum):
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"
```

---

## Error Handling

### Exception Hierarchy
```
MealTrackException (base)
├── ValidationException → 400
├── ResourceNotFoundException → 404
├── BusinessLogicException → 422
├── ConflictException → 409
├── ExternalServiceException → 503
├── AuthenticationException → 401
└── AuthorizationException → 403
```

### Usage in Handlers
```python
async def handle(self, query: GetMealByIdQuery) -> Meal:
    meal = self.meal_repo.find_by_id(query.meal_id)
    if not meal:
        raise ResourceNotFoundException(
            message=f"Meal {query.meal_id} not found",
            error_code="MEAL_NOT_FOUND",
            details={"meal_id": query.meal_id}
        )
    return meal
```

## Logging Ownership

**Core rule: log-or-raise, not both.** Every unexpected failure produces exactly one root-cause `ERROR` log. Expected domain exceptions (4xx) produce zero `ERROR` logs.

### Exception Owner Matrix

| Boundary | Owns ERROR log? | Notes |
|----------|----------------|-------|
| `src/api/exception_handlers.py` | Yes — unexpected exceptions only | `_unexpected_exception_handler` is the single catch-all ERROR owner |
| `src/api/exception_handlers.py` | No — expected 4xx | `_meal_track_exception_handler` converts silently, no log |
| `src/api/middleware/request_logger.py` | No | 5xx response lines are `WARNING` (outcome indicator); root-cause ERROR is elsewhere |
| Command/query handlers | No | Pure conversion via `handle_exception()` or direct propagation; do not log before re-raising |
| Event handlers / background tasks | Yes — at their boundary | These swallow exceptions, so they own the ERROR at the subscriber boundary |
| Cron entrypoints (`src/cron/`) | Yes — `capture_exception` + `flush_observability` before exit | Use `log_event("info", "cron.phase.completed")` per phase for lifecycle tracing |

### Log Level Guide

| Level | When to Use |
|-------|-------------|
| `ERROR` | Unexpected/unrecoverable: unhandled exception, broken required dependency, background task failure |
| `WARNING` | Degradation or recoverable signal: 5xx response outcome, slow request, retry, optional dependency bypass, AI provider fallback |
| `INFO` | Normal lifecycle: request completion, cron phase done, startup |

### Catch Block Examples

```python
# BAD — log-and-rethrow creates duplicate Sentry issues
try:
    result = await service.do_work()
except SomeError as e:
    logger.error("Work failed: %s", e)   # ERROR here
    raise handle_exception(e)            # ERROR again in exception_handlers.py

# GOOD — let the global handler own the single ERROR
try:
    result = await service.do_work()
except MealTrackException as e:
    raise handle_exception(e)            # pure conversion, no log

# GOOD — background handler owns its own ERROR (it swallows, not re-raises)
async def handle(self, event: SomeEvent) -> None:
    try:
        await self._process(event)
    except Exception as e:
        logger.error("Background handler failed: %s", type(e).__name__, exc_info=True)
        capture_exception(e)
```

---

## Production Logging

Use stdlib `logging` unless a file already uses the provider-neutral observability
facade. Keep direct `sentry_sdk` imports isolated to `src/infra/monitoring/sentry.py`.

### Severity Rules

| Level | Use For | Do Not Use For |
|-------|---------|----------------|
| `INFO` | Normal milestones: startup complete, background job complete, expected 2xx/3xx/most 4xx requests | Raw payloads or noisy per-item traces |
| `WARNING` | Unexpected but non-breaking events: slow requests, 429 rate limits, retries, degraded optional dependencies, invalid webhook auth | Expected 400/401/403/404 responses |
| `ERROR` | Functional failures needing engineering attention: unhandled exceptions, 5xx responses, provider failures that break a user flow | Process-fatal startup failures |
| `CRITICAL` | Page-worthy service-unusable paths: required startup dependency failure that aborts serving, core health failure | Ordinary request failures or optional integration degradation |

### Privacy Rules

Never log request/response bodies, auth headers, Firebase tokens/claims, emails,
email subjects, food payloads, raw image URLs, raw AI responses, raw provider
payloads, API keys, DSNs, or service account JSON.

Prefer stable operational metadata:

```python
logger.warning(
    "provider retry scheduled: provider=%s operation=%s error_type=%s",
    provider_name,
    operation,
    type(exc).__name__,
)
```

For AI parsing failures, log parser stage, content length, and error type rather
than a response preview. For image uploads, log generated image ID, result, and
elapsed time rather than delivery URLs. For webhooks, log event type and
environment, not alias lists or raw provider identifiers.

---

## Code Quality Checklist

- [ ] All functions have type hints
- [ ] Dataclasses used for DTOs
- [ ] Enums for constrained values
- [ ] Exceptions follow hierarchy
- [ ] File size <200 LOC (target) or <400 LOC (max)
- [ ] `snake_case.py` file names
- [ ] Pattern-based naming (command/query/event/handler/service/repo)
- [ ] No `dynamic` types (always explicit)
- [ ] Logs follow severity and privacy rules
- [ ] Run before commit: `black src/ tests/ && ruff check src/ && mypy src/`

---

See related: `testing-standards.md`, `cqrs-guide.md`
