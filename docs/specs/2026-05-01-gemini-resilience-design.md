# Gemini Resilience: Rate Limit & Model Unavailability Handling

**Date:** 2026-05-01  
**Status:** Approved  
**Scope:** Backend AI service resilience for Gemini API rate limits and overload

## Problem

Current implementation has no specific handling for Gemini model unavailability:
- All Gemini errors fall into generic `except Exception` handlers
- No concurrency limit on parallel calls (7 tasks can exhaust 5-10 RPM pools instantly)
- No backoff in retry logic (immediate retries worsen quota exhaustion)
- Silent failures return `None`, becoming HTTP 500 with no retry guidance for clients

## Requirements

| Decision | Choice |
|----------|--------|
| Error strategy | Retry once (1s backoff) → degrade to partial results → fail with 503 |
| Concurrency | 4-5 concurrent Gemini calls (semaphore) |
| Rate limit response | Brief global pause (2-5s) across all requests |
| Retry backoff | Minimal (1-2s total) — performance priority |
| Client communication | HTTP 503 + structured body with `retry_after_seconds` |

## Architecture

### New Component: GeminiThrottle

Location: `src/infra/services/ai/gemini_throttle.py`

Singleton that coordinates all Gemini API calls with:
- **Semaphore (limit=4):** Prevents more than 4 concurrent calls
- **Cooldown timestamp:** When rate limit detected, blocks new calls for 2-3 seconds
- **Thread-safe:** Uses `asyncio.Lock` for cooldown state

```python
class GeminiThrottle:
    _instance: Optional["GeminiThrottle"] = None
    _semaphore: asyncio.Semaphore  # limit=4
    _cooldown_until: float = 0
    _lock: asyncio.Lock

    @classmethod
    def get_instance(cls) -> "GeminiThrottle":
        # Singleton accessor

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        # Wait for cooldown to expire, then acquire semaphore
        # Yields when safe to make API call

    def record_rate_limit(self, retry_after: int = 3) -> None:
        # Sets cooldown_until = time.time() + retry_after
        # Called when 429/ResourceExhausted detected
```

### Modified Component: MealGenerationService

Location: `src/infra/adapters/meal_generation_service.py`

Changes to `generate_meal_plan()`:

1. Add specific error detection for rate limits
2. Add retry-once logic with 1s sleep
3. Raise `ExternalServiceException` on persistent failure

Note: `generate_meal_plan()` remains synchronous. The throttle is applied by callers before `asyncio.to_thread()`.

```python
from google.api_core.exceptions import ResourceExhausted

def generate_meal_plan(self, ...):
    for attempt in range(2):  # max 2 attempts
        try:
            response = llm.invoke(messages)
            return self._parse_response(response)
        except ResourceExhausted as e:
            if attempt == 0:
                time.sleep(1)  # sync sleep, minimal backoff
                continue
            raise ExternalServiceException(
                message="AI service temporarily unavailable",
                error_code="AI_RATE_LIMITED",
                details={"retry_after_seconds": 5, "reason": "rate_limit"}
            )
        except Exception as e:
            if is_rate_limit_error(e) and attempt == 0:
                time.sleep(1)
                continue
            raise
```

### Modified Component: Recipe Attempt Builder

Location: `src/domain/services/meal_suggestion/recipe_attempt_builder.py`

Wrap the `asyncio.to_thread()` call with throttle:

```python
async def attempt_recipe_generation(...):
    throttle = GeminiThrottle.get_instance()
    
    async with throttle.acquire():
        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(generation_service.generate_meal_plan, ...),
                timeout=PARALLEL_SINGLE_MEAL_TIMEOUT,
            )
        except ExternalServiceException:
            # Rate limit after retry — record cooldown for other requests
            throttle.record_rate_limit(retry_after=3)
            raise
```

Similarly update `parallel_recipe_generator.py` for Phase 1 and Discovery calls.

### Modified Component: Exception Handler

Location: `src/api/main.py`

Add dedicated handler for `ExternalServiceException` to include `Retry-After` header:

```python
@app.exception_handler(ExternalServiceException)
async def external_service_handler(request: Request, exc: ExternalServiceException):
    retry_after = exc.details.get("retry_after_seconds", 30)
    return JSONResponse(
        status_code=503,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        },
        headers={"Retry-After": str(retry_after)}
    )
```

### Unchanged Components

- **`gemini_model_config.py`:** Model pool distribution unchanged
- **Vision/embedding adapters:** Can add throttle later if needed

## Error Detection

### Errors to Catch

```python
# Primary: gRPC-level quota error
google.api_core.exceptions.ResourceExhausted

# Secondary: HTTP errors wrapped by LangChain
# Detected via string matching in exception message:
# - "429" (Too Many Requests)
# - "resource exhausted"
# - "503" (Service Unavailable)
# - "overloaded"
```

### Helper Function

```python
def is_rate_limit_error(e: Exception) -> bool:
    error_str = str(e).lower()
    return any(indicator in error_str for indicator in [
        "429", "resource exhausted", "resourceexhausted",
        "503", "overloaded", "quota"
    ])
```

## API Response

When AI service fails after retry:

```
HTTP 503 Service Unavailable
Retry-After: 5

{
  "error_code": "AI_RATE_LIMITED",
  "message": "AI service temporarily unavailable",
  "details": {
    "retry_after_seconds": 5,
    "reason": "rate_limit"
  }
}
```

## Graceful Degradation Flow

Existing behavior in `ParallelRecipeGenerator` already supports degradation:

```
7 recipe tasks launched
    ↓
Throttle limits to 4 concurrent
    ↓
Some fail with rate limit → return None
    ↓
Successful results collected
    ↓
len(successful) >= 2? → return partial results
    ↓
len(successful) < 2? → raise RuntimeError → becomes 503
```

No changes needed; throttle makes this more reliable by preventing cascade failures.

## Testing Strategy

### Unit Tests: GeminiThrottle

Location: `tests/unit/infra/services/ai/test_gemini_throttle.py`

| Test | Description |
|------|-------------|
| `test_semaphore_limits_concurrency` | Launch 6 tasks, assert only 4 proceed immediately |
| `test_cooldown_blocks_new_requests` | After `record_rate_limit(2)`, assert `acquire()` blocks ~2s |
| `test_cooldown_expires` | After cooldown expires, assert `acquire()` proceeds immediately |
| `test_singleton_returns_same_instance` | Assert `get_instance()` returns same object |

### Unit Tests: Error Detection

Location: `tests/unit/infra/adapters/test_meal_generation_resilience.py`

| Test | Description |
|------|-------------|
| `test_resource_exhausted_triggers_retry` | Mock ResourceExhausted once → succeed → assert result returned |
| `test_429_in_error_message_triggers_retry` | Mock "429" exception → assert same retry behavior |
| `test_persistent_failure_raises_external_service_exception` | Mock 2 failures → assert ExternalServiceException raised |
| `test_non_rate_limit_error_no_cooldown` | Mock ValueError → assert no cooldown, error propagates |

### Integration Test

Location: `tests/integration/test_gemini_rate_limit_handling.py`

| Test | Description |
|------|-------------|
| `test_parallel_recipes_with_simulated_rate_limit` | Mock 2/7 calls to fail → assert 3+ recipes returned, cooldown triggered |

## File Changes Summary

| File | Change | Lines (est.) |
|------|--------|--------------|
| `src/infra/services/ai/gemini_throttle.py` | **New** | ~60 |
| `src/infra/adapters/meal_generation_service.py` | **Modify** | ~30 |
| `src/domain/services/meal_suggestion/recipe_attempt_builder.py` | **Modify** | ~15 |
| `src/domain/services/meal_suggestion/parallel_recipe_generator.py` | **Modify** | ~20 |
| `src/api/main.py` | **Modify** | ~10 |
| `tests/unit/infra/services/ai/test_gemini_throttle.py` | **New** | ~80 |
| `tests/unit/infra/adapters/test_meal_generation_resilience.py` | **New** | ~100 |
| `tests/integration/test_gemini_rate_limit_handling.py` | **New** | ~50 |

## Out of Scope

- Vision AI adapter (`vision_ai_service.py`) — can add throttle later
- Embedding adapter (`gemini_text_embedding_adapter.py`) — can add throttle later
- Circuit breaker pattern — overkill for transient rate limits
- External retry library (tenacity) — custom solution is simpler for this use case
