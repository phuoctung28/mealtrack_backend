# Phase 03: Background Task Ownership

## Context Links

- [Plan overview](./plan.md)
- `src/infra/event_bus/background_task_manager.py`
- `src/api/dependencies/task_manager.py`
- `src/infra/services/ai/gemini_cache_manager.py`

## Overview

**Priority:** P2
**Status:** Planned

Align long-lived background work with the process task manager or make ownership
explicit in lifespan code.

## Key Insights

- Event bus background work is already managed.
- `GeminiCacheManager` still starts its own refresh task and stops it during
  lifespan shutdown.
- That is controlled today, but it creates a second pattern future refresh loops
  could copy.

## Requirements

- Do not introduce bare long-lived `asyncio.create_task()` in runtime paths.
- Preserve Gemini cache warm/refresh behavior.
- Ensure shutdown cancels or drains before Redis and DB teardown.

## Architecture

Preferred options:

```text
lifespan owns BackgroundTaskManager -> manager.spawn(refresh_loop)
```

or:

```text
lifespan creates task explicitly -> lifespan cancels/awaits task before teardown
```

Use the first option if it stays simple.

## Related Code Files

Modify:
- `src/infra/services/ai/gemini_cache_manager.py`
- `src/api/main.py`
- `tests/unit/infra/services/ai/test_gemini_cache_manager.py`
- Task-manager tests if needed

## Implementation Steps

1. Change `GeminiCacheManager.start_refresh_loop()` to accept a task manager or
   return the refresh coroutine/task owner to lifespan.
2. Update `main.py` startup wiring.
3. Update stop behavior to remain idempotent.
4. Add tests for task registration and cancellation.
5. Keep domain-local short-lived parallel tasks allowed when awaited and cleaned.

## Todo List

- [ ] Choose task ownership API.
- [ ] Update Gemini cache manager.
- [ ] Update lifespan wiring.
- [ ] Add/adjust tests.
- [ ] Run async boundary guard tests.

## Success Criteria

- No new unmanaged long-lived background task pattern.
- Shutdown still stops Gemini refresh before Redis disconnect.
- Event bus and Gemini refresh share one lifecycle story.

## Risk Assessment

- Low to medium: cache refresh is optional, but leaks can affect shutdown.
- Mitigation: keep failures non-fatal and test idempotent stop.

## Security Considerations

Background tasks must not log prompts, raw user content, API keys, or Redis
credential material.

## Next Steps

After this phase, expand static guards in Phase 6 if needed.

