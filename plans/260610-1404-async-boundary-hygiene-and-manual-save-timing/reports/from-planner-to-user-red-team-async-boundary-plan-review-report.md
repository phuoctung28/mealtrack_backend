---
type: report
title: "Red team review for async boundary hygiene plan"
created: "2026-06-10"
---

# Red Team Review

## Summary

Hostile review result: plan is valid only if it stays scoped. The dangerous failure is broad async churn that changes product behavior while trying to clean aesthetics.

## Findings

| Severity | Finding | Evidence | Disposition |
|---|---|---|---|
| High | Removing fire-and-forget publish may accidentally make request latency worse if events become awaited inline. | `src/infra/event_bus/pymediator_event_bus.py:231` | Accept: require managed background runner, not inline subscriber execution by default. |
| High | Manual save spinner may be cache invalidation latency, not async cleanup. | `src/app/handlers/command_handlers/create_manual_meal_command_handler.py:49`, `src/app/services/cache_invalidation_service.py:58` | Accept: keep manual-save timing as evidence phase before code change. |
| Medium | Direct route sessions may be async but still violate CQRS transaction ownership. | `src/api/routes/v1/feature_flags.py:33`, `src/api/routes/v1/meal_suggestions.py:68` | Accept: migrate only active writes first; read-only dependencies can remain until handler exists. |
| Medium | Sync wrapper removal can break tests that still exercise old contract. | `src/infra/adapters/meal_generation_service.py:57`, `tests/unit/infra/adapters/test_meal_generation_service_resilience.py:23` | Accept: update tests to async API or move sync wrapper to test-only helper before delete. |
| Medium | UoW lock fail-fast change could break handlers that still reuse injected UoWs. | `src/infra/database/uow_async.py:85`, `src/infra/event_bus/pymediator_event_bus.py:145` | Accept: add guardrail/report first; defer behavior change unless tests prove no reuse. |

## Plan Changes Required

- Include managed background execution design before event bus edits.
- Keep manual-save timing phase separate from async cleanup.
- Add tests before each cleanup slice.
- Avoid repository renames unless call-site churn is small and protected.

## Whole-Plan Consistency Sweep

- No contradictions after applying review notes.
- Scope remains cleanup and validation only.
- No public API response changes planned.

## Unresolved Questions

None.
