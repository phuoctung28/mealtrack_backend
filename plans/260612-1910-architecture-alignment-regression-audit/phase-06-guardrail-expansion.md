# Phase 06: Guardrail Expansion

## Context Links

- [Plan overview](./plan.md)
- `tests/architecture/test_async_boundary_hygiene.py`
- `tests/architecture/test_async_db_runtime_boundaries.py`
- `.importlinter`

## Overview

**Priority:** P2
**Status:** Complete

Add small static checks for regression classes found during the docs audit.

## Key Insights

- Existing architecture tests are useful and green.
- They catch sync DB imports, route commits, event-loop drivers, unmanaged
  route/event-bus tasks, `requests` imports in async adapters, and repo commits.
- They do not yet catch every sync `httpx.*` call or lower-layer HTTP exception
  imports.

## Requirements

- Keep guardrails targeted and low-noise.
- Prefer empty allowlists.
- If an allowlist is unavoidable, document why and shrink it later.

## Architecture

Guardrails should encode rules from
`docs/architecture/async-cqrs-feature-alignment.md`, especially:

- No blocking I/O in async runtime paths.
- No HTTP framework leakage into app/domain/infra.
- No new import-linter baseline growth.

## Related Code Files

Modify:
- `tests/architecture/test_async_boundary_hygiene.py`
- `tests/architecture/test_async_db_runtime_boundaries.py`
- `.importlinter` if Phase 1 removes exception imports

## Implementation Steps

1. Add static scan for sync `httpx.get/post/put/delete/head/patch` in async
   runtime paths.
2. Exclude sync helper methods only when they are reached by documented
   `asyncio.to_thread` wrappers.
3. Add static scan for `fastapi.HTTPException` outside API.
4. Add or tighten import-linter contracts after Phase 1.
5. Run architecture tests and `lint-imports`.

## Todo List

- [x] Add sync `httpx` guard. → `test_no_blocking_httpx_calls_in_async_runtime_paths` (with cloudinary allowlist)
- [x] Add non-API `HTTPException` guard. → `test_http_exception_not_imported_outside_api`
- [x] Tighten import-linter after exception relocation. → 2 baselines removed
- [x] Run architecture gates. → 16/16 pass, 4/4 contracts kept

## Success Criteria

- A new blocking sync HTTP call in async runtime fails tests.
- A lower-layer `HTTPException` import fails tests.
- All existing architecture gates remain green.

## Risk Assessment

- Low: static checks can be noisy if overbroad.
- Mitigation: scan specific runtime directories and keep error messages clear.

## Security Considerations

HTTP exception leakage can expose transport concerns and inconsistent error
payloads. Blocking HTTP calls can become availability issues under load.

## Next Steps

Add these guards after Phase 1 or alongside it so the newly cleaned boundaries
stay clean.

