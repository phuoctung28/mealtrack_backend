---
phase: 3
title: "Async external client alignment"
status: complete
priority: P1
effort: "3-4 days"
dependencies: [1]
---

# Phase 3: Async external client alignment

## Context Links

- Research: `./research/async-library-scout.md`
- USDA adapter: `src/infra/adapters/food_data_service.py`
- Cloudinary adapter: `src/infra/adapters/cloudinary_image_store.py`
- Existing async examples: `src/infra/adapters/open_food_facts_service.py`,
  `src/infra/adapters/fat_secret_service.py`

## Overview

Remove active sync HTTP calls from async service paths where a real async
library exists. For sync-only vendor SDKs, add explicit off-loop async methods
instead of pretending the SDK is async.

## Requirements

- Functional: `FoodDataService` no longer uses `requests.Session` in async
  methods.
- Functional: Cloudinary blocking operations are not called directly from async
  handlers/routes.
- Functional: existing image storage behavior and URLs remain compatible.
- Non-functional: no broad shared-client framework unless duplication proves it.
- Non-functional: sync-only migration/admin tooling is out of scope.

## Architecture

Use three categories:

1. Native async client exists: use `httpx.AsyncClient`.
2. Vendor SDK is sync-only: expose async wrapper methods using
   `asyncio.to_thread` / executor at the adapter boundary.
3. Tests/scripts only: keep sync library only if not imported by active runtime.

Cloudinary should likely keep sync `ImageStorePort` for compatibility and add an
async interface or async methods for runtime callers:

```python
class CloudinaryImageStore:
    async def save_async(...): return await asyncio.to_thread(self.save, ...)
```

Then migrate async handlers/routes to await those methods.

## Related Code Files

- Modify: `src/infra/adapters/food_data_service.py`
- Modify: `src/domain/ports/food_data_service_port.py`
- Modify: `src/infra/adapters/cloudinary_image_store.py`
- Modify: `src/domain/ports/image_store_port.py` or create async companion port
- Modify: `src/app/handlers/event_handlers/meal_analysis_event_handler.py`
- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Modify: `src/api/routes/v1/meals.py`
- Modify: `src/api/base_dependencies.py`
- Modify: `tests/unit/infra/test_cloudinary_image_store.py`
- Create/Modify: tests for async FoodDataService behavior
- Modify: `pyproject.toml`, `requirements.txt` only after active `requests`
  runtime imports are gone.

## Implementation Steps

1. Add tests that fail if `FoodDataService.search_foods`, `get_food_details`,
   or `get_multiple_foods` use blocking `requests` in async methods.
2. Convert `FoodDataService` to `httpx.AsyncClient` with injectable client or
   transport for tests.
3. Add close/lifecycle handling only if a persistent client is introduced.
   Prefer simple per-call client first unless benchmarks show need.
4. Audit Cloudinary call sites:
   - uploads in command handlers
   - image load during analysis
   - `get_url` in routes
   - delete/load tests
5. Add async wrapper methods for blocking Cloudinary SDK operations and migrate
   async runtime call sites to those wrappers.
6. Add a runtime static guard:
   - block `import requests` under `src/infra/adapters` unless a file is
     explicitly classified as sync-only and off-loop.
7. Remove `requests` from runtime dependencies only if no active source imports
   remain. Otherwise document why it remains.

## Success Criteria

- [x] USDA/FoodDataService uses `httpx.AsyncClient`, not `requests`.
- [x] Async handlers do not call Cloudinary sync methods directly.
- [x] Existing Cloudinary behavior remains backward compatible.
- [x] Static guard documents any remaining sync-only allowlist.
- [x] Tests cover timeout/error behavior for converted adapters.

## Risk Assessment

Risk: changing `ImageStorePort` to async breaks many tests and mocks.

Mitigation: add async methods or companion port first; migrate runtime callers
without deleting sync compatibility until tests are stable.

Risk: Cloudinary SDK has no first-party async replacement.

Mitigation: use off-loop wrapper and document why this is containment, not an
async library swap.
