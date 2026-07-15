---
title: "Meal Analyze LangGraph Provider Workflow"
description: "Add a sync-compatible LangGraph workflow for meal image analysis while preserving current API behavior and provider boundaries."
status: completed
priority: P1
effort: "4-6d"
branch: "delivery"
tags: [backend, ai, vision, refactor, critical]
blockedBy: []
blocks: []
created: "2026-07-07"
createdBy: "ck:plan"
source: skill
mode: tdd
brainstorm: "../reports/260707-1342-meal-analyze-langgraph-provider-brainstorm.md"
---

# Meal Analyze LangGraph Provider Workflow

## Overview

Implement the approved sync-compatible LangGraph workflow for MealTrack image
analysis. The API remains synchronous: valid scans return READY
`DetailedMealResponse`, not background `PROCESSING`.

Scope is all meal image entrypoints: direct upload, meal scan-by-url, and
food-label scan-by-url. Existing provider boundaries stay intact.

## Phases

| Phase | Name | Status | Effort |
|-------|------|--------|--------|
| 1 | [Baseline Contracts](./phase-01-baseline-contracts.md) | Completed | 0.5-1d |
| 2 | [Graph Scaffold And Feature Flags](./phase-02-graph-scaffold-and-feature-flags.md) | Completed | 1d |
| 3 | [Shared Workflow Integration](./phase-03-shared-workflow-integration.md) | Completed | 1-2d |
| 4 | [Optional FatSecret Validation](./phase-04-optional-fatsecret-validation.md) | Completed | 1d |
| 5 | [Rollout, Docs, And Verification](./phase-05-rollout-docs-and-verification.md) | Completed | 0.5-1d |

## Architecture Direction

`API route -> command handler -> MealAnalyzeWorkflow -> meal_analyze_graph -> VisionAIService / parser / optional validation -> UoW -> DetailedMealResponse -> profile-aware value insight task`

Rules:
- Domain layer must not import LangGraph.
- Graph nodes must not import vendor SDKs, `sentry_sdk`, or raw SQL.
- `VisionAIService` and `AIModelManager` remain provider source of truth.
- `food_reference` is reused first; no Sprint 1 schema migration.
- FatSecret validation is default-off and never required for a valid scan.

## Scope Notes

- HOLD SCOPE: no new DB tables, meal statuses, background jobs, or provider reorder.
- Related only: `260623-1450-cloudflare-ai-gateway-vision`.
- Related only: `260612-1046-service-initiated-bandwidth-reduction`.
- Completed prerequisite: `260627-1322-meal-scan-prompt-and-beverage-simplification`.

## Success Criteria

- Current direct upload, scan-by-url, and food-label responses remain compatible.
- Graph disabled path preserves legacy handler behavior.
- Graph enabled path produces equivalent READY meals for valid scans.
- Food-label scan keeps `food_label_metadata` and label-specific parsing.
- FatSecret staged detail fetch avoids `food.get.v5` for every search hit.
- Meal value insights are scheduled for image and URL scans without blocking READY responses.
- User profile context is included in meal value insight cache version and AI prompt.
- Provider outage, FatSecret timeout, and no-food paths remain controlled.
- Focused unit tests, architecture guardrails, and smoke tests pass.

## Out Of Scope

- Background processing or mobile polling.
- New persisted `READY_WITH_WARNINGS` status.
- New DB tables for external mappings or payload cache.
- New PostHog product analytics.
- USDA/OpenFoodFacts expansion beyond existing barcode/food-label behavior.
- Changing OpenAI/Cloudflare provider ordering.

## Handoff
```bash
/ck:cook /Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/260707-1348-meal-analyze-langgraph-provider/plan.md --tdd
/ck:plan red-team /Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/260707-1348-meal-analyze-langgraph-provider
```
