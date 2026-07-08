---
title: "Meal Analyze LangGraph Provider Implementation"
date: "2026-07-07"
plan: "plans/260707-1348-meal-analyze-langgraph-provider/plan.md"
status: completed
---

# Meal Analyze LangGraph Provider Implementation

## Context

Meal image analysis needed a LangGraph-ready workflow without changing the
current synchronous mobile/API contract. Direct upload, scan-by-url, and
food-label scan-by-url all had to stay READY-on-success by default.

## What Happened

- Added a default-off `MealAnalyzeWorkflow` and app-layer graph scaffold.
- Routed direct upload and scan-by-url through the graph only when
  `AI_MEAL_ANALYZE_GRAPH_ENABLED` is enabled.
- Added optional, default-off FatSecret reference validation with local-first
  batch lookup and conservative allowed-unit enrichment.
- Kept food-label scans out of FatSecret validation.
- Removed raw URL state from the graph boundary; URL scans pass only an image id.
- Added a post-persist meal insight graph step and shared scheduler.
- Meal value insights now fetch compact user profile context when available.
- Updated rollout, external-services, and architecture docs.

## Decisions

- Keep API synchronous for this phase.
- Keep graph and FatSecret validation independently env-gated.
- Reuse existing handlers behind a workflow seam instead of rewriting provider
  orchestration.
- Treat FatSecret as best-effort enrichment, never as a hard dependency for valid
  meal scans.
- Keep meal insight AI in the background so READY scan responses stay fast.

## Verification

- `uv run pytest ... --import-mode=importlib`: 63 focused tests passed.
- `uv run python -m compileall src tests`: passed.
- `uv run ruff check ...`: passed.

## Next

- Enable graph in staging first.
- Enable FatSecret validation separately after graph behavior is observed.
- Monitor latency and provider error rate before production rollout.
