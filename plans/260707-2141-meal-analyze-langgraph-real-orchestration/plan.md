---
title: "Meal Analyze LangGraph Real Orchestration"
description: "Move real meal image analysis orchestration into LangGraph nodes while preserving the synchronous READY response contract."
status: completed
priority: P1
effort: "3-5d"
branch: "delivery"
tags: [backend, ai, vision, langgraph, refactor]
blockedBy: []
blocks: []
created: "2026-07-07"
createdBy: "ck:plan"
source: skill
mode: deep-tdd
related:
  - "260707-1348-meal-analyze-langgraph-provider"
  - "260623-1450-cloudflare-ai-gateway-vision"
  - "260612-1046-service-initiated-bandwidth-reduction"
---

# Meal Analyze LangGraph Real Orchestration

## Overview

Current LangGraph path is a wrapper: it records metadata then delegates to
legacy handlers. This plan makes LangGraph own meaningful workflow steps:
image acquisition, mode routing, vision analysis, parsing, optional reference
validation, persistence, cache invalidation, and insight scheduling.

API stays synchronous. Valid scans still return READY `DetailedMealResponse` in
the same request. No mobile polling, no new DB tables, no provider reorder.

## Scope Challenge

- Existing code: `MealAnalyzeWorkflow`, graph scaffold, legacy handlers,
  `VisionAIService`, `FoodReferenceValidationService`, and insight scheduler.
- Minimum changes: move orchestration into graph nodes; keep provider internals
  and API response contracts unchanged.
- Complexity: touches >8 files because routing, graph, tests, and docs all need
  coverage. New abstractions limited to graph runtime/context + app scheduler.
- Selected mode: HOLD SCOPE, deep TDD.

## Target Flow

```text
API route
 -> command handler
 -> MealAnalyzeWorkflow
 -> LangGraph:
    prepare_input
    -> acquire_image
    -> choose_analysis_strategy
    -> analyze_vision
    -> parse_nutrition
    -> validate_reference?          # meal scans only, flag-gated
    -> persist_meal
    -> invalidate_cache
    -> schedule_value_insights
    -> complete
 -> handler returns READY Meal
```

Graph state must contain only safe structured metadata and domain objects. Raw
image bytes, raw URLs, provider clients, and UoW instances stay in runtime-bound
node dependencies, not persisted state.

## Phases

| Phase | Name | Status | Effort |
|-------|------|--------|--------|
| 1 | [Regression Map](./phase-01-regression-map.md) | Complete | 0.5d |
| 2 | [Graph Runtime And Acquisition Nodes](./phase-02-graph-runtime-and-acquisition-nodes.md) | Complete | 1d |
| 3 | [Vision Parse Validate Persist Nodes](./phase-03-vision-parse-validate-persist-nodes.md) | Complete | 1-2d |
| 4 | [Insight Scheduling Docs And Rollout](./phase-04-insight-scheduling-docs-and-rollout.md) | Complete | 0.5-1d |

## Dependencies

- Requires completed `260707-1348-meal-analyze-langgraph-provider`.
- Related to `260623-1450-cloudflare-ai-gateway-vision`, but not blocked by it.
- Must preserve `260612-1046-service-initiated-bandwidth-reduction` safe bytes
  path: scan-by-url may download/compress, but never sends raw URL to AI.

## Success Criteria

- Graph-enabled path has observable behavior beyond metadata marking.
- Direct upload, scan-by-url, and food-label scan-by-url all execute through
  graph nodes when `AI_MEAL_ANALYZE_GRAPH_ENABLED=true`.
- Graph-disabled path remains legacy/default.
- READY response, no-food rejection, food-label metadata, cache invalidation,
  and mobile DTOs stay compatible.
- Raw image URLs and bytes do not appear in graph state tests.
- Focused unit, architecture, compile, and ruff gates pass.

## Progress Notes

- 2026-07-07: Added runtime-bound graph acquisition for upload and
  scan-by-url, with raw bytes/URLs kept out of graph state.
- 2026-07-07: Added runtime graph nodes for vision analysis, nutrition parsing,
  optional reference-validation marking, READY meal persistence, and cache
  invalidation.
- 2026-07-07: Wired graph-enabled upload and scan-by-url handlers to pass real
  runtime dependencies so they no longer delegate back to legacy handlers when
  the graph flag is enabled.
- 2026-07-07: Phase 3 parity fixes covered crop food-label persistence,
  best-effort translation failures, and upload retry attempts.
- 2026-07-07: Phase 4 planning refined around moving the existing API-layer
  insight scheduler into the application layer, then invoking it from graph
  runtime after cache invalidation.
- 2026-07-07: Phase 4 implementation moved the scheduler into `src/app/services`,
  added graph-owned best-effort insight scheduling after cache invalidation,
  kept API fallback/refresh compatibility, and updated rollout docs.
- 2026-07-07: Phase 4 completed with smoke-style test coverage proving READY
  graph response returns before scheduled value-insight AI generation, followed
  by `meal_value_insights.cache_saved` from the captured background coroutine.

## Out Of Scope

- Background meal processing status or mobile polling.
- New persisted meal statuses/tables/checkpoints.
- Provider ordering, Cloudflare/Gemini/OpenAI internals, or gateway routing.
- New product analytics.
