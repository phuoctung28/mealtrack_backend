---
phase: 1
title: "Regression Map"
status: complete
priority: P1
effort: "0.5d"
dependencies: []
---

# Phase 1: Regression Map

## Overview

Lock the current legacy and graph-enabled contracts before moving behavior into
nodes. The goal is to prove what must not change.

## Context Links

- Current plan: `plans/260707-1348-meal-analyze-langgraph-provider/plan.md`
- Upload handler: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Scan-by-url handler: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Graph scaffold: `src/app/graphs/meal_analyze/`
- Existing tests: `tests/unit/handlers/command_handlers/test_upload_image_consistency.py`
- Existing tests: `tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py`

## Requirements

- Functional: graph-enabled and graph-disabled paths produce equivalent READY
  meals for valid scans.
- Functional: no-food, schema validation, and food-label failures do not persist
  normal meals.
- Non-functional: graph state never exposes raw image bytes or raw URLs.

## Architecture

Tests should define the migration contract, not the final implementation. Use
existing fake UoWs and AsyncMocks where possible. Add graph-state guardrails in
architecture tests.

## Related Code Files

- Modify: `tests/unit/app/services/test_meal_analyze_workflow.py`
- Modify: `tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py`
- Modify: `tests/unit/architecture/test_meal_analyze_graph_boundaries.py`
- Modify: handler regression tests for upload and scan-by-url.

## Tests Before

1. Add graph-state tests asserting no `image_url`, raw bytes, provider clients,
   UoW, or cache objects can enter public state.
2. Add equivalence tests around graph-enabled upload and scan-by-url path.
3. Add food-label test proving validation node is skipped for food labels.

## Refactor

No production refactor in this phase except tiny test hooks if needed.

## Tests After

- Focused tests from modified files pass.
- Architecture guardrail fails if graph imports infra/provider SDKs directly.

## Implementation Steps

1. Enumerate current entrypoint behaviors and failure cases.
2. Add missing graph-enabled regression cases.
3. Add state-safety architecture checks.
4. Run focused handler, graph, and architecture tests.

## Success Criteria

- [x] Tests fail if graph state carries sensitive payloads.
- [x] Tests fail if graph-enabled path stops returning READY meal equivalents.
- [x] Tests fail if food-label flow enters meal-scan reference validation.

## Risk Assessment

- Risk: tests mirror implementation too tightly.
- Mitigation: assert user-visible contracts and state boundaries, not exact node
  call order except where graph ownership matters.
