---
phase: 4
title: "Sync compatibility wrapper cleanup"
status: complete
priority: P2
effort: "1-2d"
dependencies: [1]
---

# Phase 4: Sync Compatibility Wrapper Cleanup

## Context Links

- [Asyncio usage research](./research/asyncio-usage-research.md)
- `src/infra/adapters/meal_generation_service.py`
- `src/domain/ports/meal_generation_service_port.py`
- `tests/unit/infra/adapters/test_meal_generation_service_resilience.py`

## Overview

Remove or quarantine sync compatibility wrappers that drive event loops. Keep explicit off-loop wrappers for vendor SDKs where no async SDK exists.

## Key Insights

- Production code appears to call `generate_meal_plan_async`; sync `generate_meal_plan()` is test-only now.
- The port already warns that wrapping sync generation can cause event-loop mismatch.
- Do not remove valid `to_thread` wrappers for Cloudinary, DeepL, Resend, Gemini SDK, Firebase auth, or CPU-bound embedding work.

## Requirements

- Functional: no runtime source calls `asyncio.get_event_loop`, `asyncio.set_event_loop`, or `run_until_complete`.
- Functional: meal generation tests use async API or a test-only helper.
- Functional: architecture test blocks future event-loop-driving wrappers.
- Non-functional: no change to AI generation outputs.

## Architecture

Prefer one async interface for LLM generation. If sync compatibility is needed for scripts/tests, keep it outside runtime adapter code or make it fail fast when called inside a running loop.

## Related Code Files

- Modify: `src/infra/adapters/meal_generation_service.py`
- Modify: `src/domain/ports/meal_generation_service_port.py`
- Modify: `tests/unit/infra/adapters/test_meal_generation_service_resilience.py`
- Modify: `tests/architecture/test_async_db_runtime_boundaries.py` or new async-boundary guard test

## Implementation Steps

1. Tests before: convert meal generation service resilience tests to async API.
2. Add static test forbidding `run_until_complete` and ambient event loop creation in `src/`.
3. Remove `generate_meal_plan()` from runtime adapter if no active `src/` caller exists.
4. If port compatibility requires the sync method, mark it deprecated and fail fast with clear error when called.
5. Verify all `src/` call sites use `generate_meal_plan_async`.
6. Run targeted tests.

## Success Criteria

- [x] `rg "run_until_complete|get_event_loop|set_event_loop" src` has no runtime hits.
- [x] Meal generation tests pass through async API.
- [x] No production code wraps async LLM generation in `to_thread`.
- [x] Legitimate vendor SDK `to_thread` wrappers remain documented and tested.

## Risk Assessment

Risk: hidden script or admin caller uses sync method. Mitigation: search scripts and tests; if needed, move helper to script-local utility.

Risk: overzealous static test blocks pytest fixtures. Mitigation: scan only `src/` runtime files.

## Security Considerations

No direct security change. Cleaner async execution reduces partial failure and resource leak risk.

## Next Steps

Phase 5 validates the manual meal save symptom with timing evidence.
