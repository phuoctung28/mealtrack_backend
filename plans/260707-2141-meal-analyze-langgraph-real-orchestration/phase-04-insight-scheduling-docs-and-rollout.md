---
phase: 4
title: "Insight Scheduling Docs And Rollout"
status: complete
priority: P1
effort: "0.5-1d"
dependencies: [3]
---

# Phase 4: Insight Scheduling Docs And Rollout

## Overview

Make meal value insight scheduling part of the graph-owned flow, update docs so
the new LangGraph path is materially different from legacy, and keep rollout
safe behind the existing feature flag.

Current state: routes schedule value insights after command handler returns.
The user's smoke-test log confirms this still works, but it is not graph-owned:
the READY response returns, then a Cloudflare text call generates and caches
`meal-value-insights:v10:*`.

## Context Links

- Insight service: `src/domain/services/meal_value_insight_service.py`
- Current scheduler: `src/api/services/meal_value_insight_scheduler.py`
- Graph nodes: `src/app/graphs/meal_analyze/nodes.py`
- Workflow service: `src/app/services/meal_analyze_workflow.py`
- API route docs: `docs/api-endpoints.md`
- Architecture docs: `docs/system-architecture.md`

## Requirements

- Functional: graph schedules profile-aware meal value insights after meal
  persistence and cache invalidation.
- Functional: scheduling remains best-effort and never blocks READY response.
- Functional: `GET /v1/meals/{meal_id}/value-insights` remains a compatibility
  and refresh/status endpoint, not the primary producer for image scans.
- Functional: both API routes and graph nodes use the same scheduling service.
- Non-functional: application layer must not import API-layer services.
- Non-functional: graph state stores only `meal_value_insight_scheduled` and
  optionally a safe scheduler source/status string. No task manager, cache,
  event bus, AI manager, profile data, raw prompt, or coroutine in graph state.
- Non-functional: existing `GET /v1/meals/{meal_id}/value-insights` response
  status values remain unchanged.

## Architecture

Move the existing scheduler boundary from `src/api/services` into
`src/app/services` so both API routes and graph nodes can call it without
application-layer imports from API.

Keep the scheduler shape simple:

```python
def schedule_value_insight_generation(
    task_manager: BackgroundTaskManager | None,
    meal: Meal,
    *,
    language: str,
    cache_service: CachePort | None,
    ai_manager: MealInsightAIPort,
    event_bus: EventBus,
    user_id: str,
    source: str = "api",
) -> bool:
    ...
```

Return `True` when a background task is spawned, `False` when prerequisites are
missing or scheduling is intentionally skipped. Existing callers may ignore the
return value.

Target flow:

```text
persist_meal
 -> invalidate_cache
 -> schedule_value_insights
 -> complete
```

State stores only the scheduled outcome:

```python
{
    "meal_id": "...",
    "meal_value_insight_scheduled": True,
    "meal_value_insight_source": "meal_analyze_graph",
}
```

The scheduler runtime dependency may hold `task_manager`, cache service, user
profile repository, and AI service dependencies. Those dependencies must not be
serialized into graph state.

## Related Code Files

- Create: `src/app/services/meal_value_insight_scheduler.py`
- Delete or leave compatibility shim: `src/api/services/meal_value_insight_scheduler.py`
- Modify: `src/api/routes/v1/meals.py`
- Modify: `src/api/routes/v1/meal_scan_by_url.py`
- Modify: `src/app/graphs/meal_analyze/nodes.py`
- Modify: `src/app/graphs/meal_analyze/runtime.py`
- Modify: `src/app/graphs/meal_analyze/state.py`
- Modify: `src/app/graphs/meal_analyze/graph.py`
- Modify: `src/app/services/meal_analyze_workflow.py`
- Modify: `src/api/dependencies/event_bus.py` if graph runtime needs scheduler
  dependencies from the composition root.
- Move/modify tests: `tests/unit/api/services/test_meal_value_insight_scheduler.py`
  -> `tests/unit/app/services/test_meal_value_insight_scheduler.py`
- Modify: `tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py`
- Modify: `tests/unit/api/test_meal_scan_by_url_insights.py`
- Modify/add: `tests/unit/architecture/test_meal_analyze_graph_boundaries.py`
- Modify: `docs/system-architecture.md`
- Modify: `docs/api-endpoints.md`
- Modify: `docs/guides/meal-analyze-fastpath-rollout.md`
- Modify: `docs/project-changelog.md` if present.

## File Inventory

| File | Action | Why |
|------|--------|-----|
| `src/api/services/meal_value_insight_scheduler.py` | move/shim | remove API-layer ownership of scheduler |
| `src/app/services/meal_value_insight_scheduler.py` | create | shared app-layer scheduler for API + graph |
| `src/api/routes/v1/meals.py` | modify imports only | preserve get/status route behavior |
| `src/api/routes/v1/meal_scan_by_url.py` | modify imports only, possibly remove duplicate scheduling when graph on | avoid double scheduling |
| `src/app/graphs/meal_analyze/runtime.py` | modify | carry scheduler deps in runtime, not state |
| `src/app/graphs/meal_analyze/nodes.py` | modify | add `schedule_value_insights` node |
| `src/app/graphs/meal_analyze/graph.py` | modify | insert node after cache invalidation |
| `src/api/dependencies/event_bus.py` | modify if needed | compose runtime with task manager/cache/AI/event bus |
| tests under `tests/unit/app` and `tests/unit/api` | modify/add | prove graph/API parity |
| docs under `docs/` | modify | document graph-owned insight producer |

## Tests Before

1. Move scheduler unit tests to app-layer imports and watch old import fail if
   app scheduler does not exist.
2. Graph integration test: scheduler is called after successful persist and
   after cache invalidation.
3. Graph failure test: scheduler is not called when scan fails before
   persistence.
4. Graph resilience test: scheduler exception/missing dependency logs and
   returns READY meal.
5. Food-label graph test: food-label scan schedules insights with
   `source="meal_analyze_graph"` after READY persistence.
6. API test: scan-by-url route still schedules insights when graph is disabled.
7. API test: scan-by-url route does not double-schedule when command graph
   already scheduled insights. This may use a safe marker on returned meal or
   runtime state if exposed through workflow.
8. API test: `GET /value-insights` still returns cached insight or triggers
   refresh behavior expected by existing clients.
9. Architecture test: no `src.app` file imports `src.api.services`.

## Refactor

Recommended implementation shape:

```python
scheduled = schedule_value_insight_generation(
    runtime.meal_value_insight_task_manager,
    runtime.saved_meal,
    language=runtime.command.language,
    cache_service=runtime.meal_value_insight_cache,
    ai_manager=runtime.meal_value_insight_ai_manager,
    event_bus=runtime.event_bus,
    user_id=runtime.command.user_id,
    source="meal_analyze_graph",
)
```

Graph node:

```text
invalidate_cache
 -> schedule_value_insights
 -> complete
```

API routes:

- `GET /{meal_id}` and `GET /{meal_id}/value-insights` keep their current
  cache-first behavior and schedule on cache miss.
- `POST /scan-by-url` keeps scheduling for graph-disabled legacy command path.
- If graph-enabled path already scheduled, route should not schedule a second
  task for the same meal in the same request.

## Tests After

- Focused graph suites pass.
- Existing value-insight route tests pass.
- Architecture guardrail confirms `src/app` does not import `src/api/services`.
- Ruff and compile checks pass for touched graph/app/API files.
- Manual smoke path: one graph-enabled meal scan returns READY before the
  insight Cloudflare call completes, then logs `meal_value_insights.cache_saved`.

## Implementation Steps

1. Move scheduler module to `src/app/services/meal_value_insight_scheduler.py`.
   Keep function names stable. Add `source` parameter and boolean return.
2. Update route imports in `src/api/routes/v1/meals.py` and
   `src/api/routes/v1/meal_scan_by_url.py`.
3. Add architecture guardrail for `src/app` not importing `src/api.services`.
4. Extend `MealAnalyzeRuntime` with optional scheduler dependencies:
   task manager, cache service, AI manager, event bus.
5. Add `schedule_value_insights` graph node. It should:
   - no-op when no saved meal exists.
   - no-op when scheduler deps are missing.
   - call scheduler after cache invalidation.
   - catch/log exceptions and keep READY response.
   - return only safe state fields.
6. Wire graph edge: `invalidate_cache -> schedule_value_insights -> complete`.
7. Compose graph runtime dependencies in handler/event-bus setup. Prefer using
   existing DI objects; do not create AI/cache/task dependencies inside nodes.
8. Prevent duplicate scheduling in routes for graph-enabled command results.
   Use the smallest marker that does not change public response contracts.
9. Update docs:
   - `docs/system-architecture.md`: app-layer scheduler + graph flow.
   - `docs/api-endpoints.md`: value-insight endpoint is status/refresh
     compatibility.
   - rollout guide: flags, FatSecret credential caveat, rollback.
10. Run focused tests, architecture tests, ruff, compile.

## Success Criteria

- [x] Meal insight scheduling is part of the graph-owned successful scan flow.
- [x] `GET /value-insights` remains compatible but is no longer required to
      create insights after image scans.
- [x] Graph-enabled and graph-disabled rollout path is documented.
- [x] Architecture layering stays clean.
- [x] Failure to schedule insights never fails the meal analysis response.
- [x] Graph-enabled route does not schedule duplicate insight tasks.
- [x] Graph state excludes scheduler dependencies and profile/AI prompt data.
- [x] Smoke logs show READY response can complete independently of insight AI
      generation.

## Progress Notes

- 2026-07-07: Moved meal value insight scheduler into `src/app/services` with
  API compatibility shim, boolean scheduling result, and explicit scheduler
  source.
- 2026-07-07: Added graph scheduling node after cache invalidation. Runtime
  dependencies stay out of graph state; failures log and return READY state.
- 2026-07-07: Updated scan-by-url route to avoid same-request duplicate
  scheduling when graph already scheduled insights.
- 2026-07-07: Updated architecture/API/rollout docs. Focused tests, handler
  wiring tests, ruff, and compile checks pass locally.
- 2026-07-07: Added smoke-style graph test proving READY returns before the
  scheduled insight AI call runs, then the captured background coroutine emits
  `meal_value_insights.cache_saved`.

## Risk Assessment

- Risk: moving the scheduler changes route behavior.
- Mitigation: keep the public route contract covered by tests before moving
  imports.

- Risk: background task failures become hidden.
- Mitigation: log source, meal id, user id, and exception class in the scheduler
  while returning success for the meal scan path.

- Risk: double scheduling from graph node plus API route.
- Mitigation: add a same-request duplicate test and keep task name stable as
  `meal-value-insights:{meal_id}`.

- Risk: app-layer scheduler imports infrastructure-only runtime classes.
- Mitigation: type against ports where possible. Keep concrete
  `BackgroundTaskManager` import only if already treated as app-safe; otherwise
  introduce a tiny scheduler task port in a later pass.

- Risk: graph node accidentally blocks READY response by awaiting insight AI.
- Mitigation: scheduler node must only spawn background work, never await
  `build_value_insights_for_meal_with_profile`.
