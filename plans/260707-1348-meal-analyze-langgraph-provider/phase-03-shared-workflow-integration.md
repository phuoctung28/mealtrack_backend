---
phase: 3
title: "Shared Workflow Integration"
status: completed
priority: P1
effort: "1-2d"
dependencies: [2]
---

# Phase 3: Shared Workflow Integration

## Context Links

- Direct upload handler: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Scan-by-url handler: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Graph package: `src/app/graphs/meal_analyze/`
- Parser: `src/domain/parsers/vision_response_parser.py`
- Strategy factory: `src/domain/strategies/meal_analysis_strategy.py`

## Overview

Extract shared scan orchestration into a workflow service and route direct upload,
meal scan-by-url, and food-label scan-by-url through it when the graph flag is
enabled. Legacy path remains available when disabled.

## Key Insights

- Direct upload owns Cloudinary upload; scan-by-url owns safe bytes download.
- Both should converge after image bytes, image metadata, scan mode, user context, and target date are known.
- Food-label scan must keep `FoodLabelImageAnalysisStrategy`, label parser, source, and metadata.

## Requirements

- Functional: graph-enabled direct upload returns equivalent READY scanner meal.
- Functional: graph-enabled scan-by-url returns equivalent READY scanner meal.
- Functional: graph-enabled food-label scan returns equivalent READY food-label meal.
- Functional: graph-disabled handlers keep legacy behavior.
- Non-functional: no public API response shape change.
- Non-functional: no duplicate provider calls.

## Architecture

```text
UploadMealImageImmediatelyHandler
  -> upload image
  -> if graph flag: MealAnalyzeWorkflow.run_uploaded(...)
  -> else: legacy path

ScanByUrlCommandHandler
  -> download bytes
  -> if graph flag: MealAnalyzeWorkflow.run_by_url(...)
  -> else: legacy path

MealAnalyzeWorkflow
  -> graph.invoke(state)
  -> services perform vision/parser/persistence
```

Recommended app service:

```text
src/app/services/meal_analyze_workflow.py
```

Keep transaction ownership explicit. The workflow may use UoW, but graph nodes
must not open raw DB sessions or SQL.

## Related Code Files

- Create: `src/app/services/meal_analyze_workflow.py`
- Modify: `src/app/graphs/meal_analyze/state.py`
- Modify: `src/app/graphs/meal_analyze/nodes.py`
- Modify: `src/app/graphs/meal_analyze/graph.py`
- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Modify: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Modify: `src/api/dependencies/event_bus.py`
- Modify: `tests/unit/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py`
- Modify: `tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py`
- Create: `tests/unit/app/services/test_meal_analyze_workflow.py`
- Create: `tests/unit/app/graphs/test_meal_analyze_graph_execution.py`

## Tests Before

1. Add failing tests for graph-enabled direct upload equivalence.
2. Add failing tests for graph-enabled scan-by-url equivalence.
3. Add failing tests for graph-enabled food-label equivalence.
4. Add failing test that graph-disabled path does not instantiate workflow.
5. Add failing no-food graph path test that no meal is saved.

## Refactor

1. Extract common "vision -> parser -> meal object -> save -> translation -> cache invalidation" behavior into workflow service.
2. Keep upload/download preparation in the existing handlers.
3. Add graph nodes that call workflow service methods or state-bound callables, not infrastructure vendors.
4. Wire workflow into handlers through composition root.
5. Keep legacy path until graph flag is enabled.

## Tests After

1. Add coverage for:
   - user description strategy
   - target date timezone behavior
   - translation failure remains non-fatal
   - cache invalidation still awaited
2. Re-run Phase 1 baseline tests in graph-disabled and graph-enabled settings where practical.

## Implementation Steps

1. Design workflow input DTO for uploaded bytes vs downloaded URL source.
2. Add workflow service with dependency injection:
   - UoW
   - VisionAIService
   - VisionResponseParser
   - translation service
   - cache invalidation
   - settings/feature flags
3. Move meal construction and persistence into reusable workflow methods.
4. Update graph nodes to invoke workflow actions in order.
5. Update handlers to branch by `AI_MEAL_ANALYZE_GRAPH_ENABLED`.
6. Update event bus wiring to pass workflow dependencies.
7. Run focused tests and compile.

## Todo List

- [x] Workflow input/output types defined.
- [x] Direct upload graph-enabled path implemented.
- [x] Scan-by-url graph-enabled path implemented.
- [x] Food-label graph-enabled path implemented.
- [x] Legacy disabled path preserved.
- [x] No-food no-persistence behavior preserved.
- [x] Focused tests pass.

## Success Criteria

- [x] All three entrypoints can run through graph path behind flag.
- [x] Legacy path remains default and passes existing tests.
- [x] No mobile/API response contract changes.
- [x] Tests pass:

```bash
uv run pytest tests/unit/app/services/test_meal_analyze_workflow.py tests/unit/app/graphs/test_meal_analyze_graph_execution.py -q
uv run pytest tests/unit/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py tests/unit/handlers/command_handlers/test_food_guard_command_handlers.py -q
```

## Risk Assessment

- Risk: refactor changes meal timestamps or timezone handling.
  Mitigation: regression tests assert target-date and current-date behavior.
- Risk: workflow duplicates UoW ownership.
  Mitigation: one UoW transaction per save; translation remains after commit as current behavior requires.
- Risk: graph nodes become hidden dependency containers.
  Mitigation: keep workflow service as orchestration owner; graph state stays explicit.

## Security Considerations

- Do not put raw image bytes in logs, graph metrics, or persisted run state.
- Keep user descriptions sanitized before workflow invocation.

## Regression Gate

```bash
uv run python -m compileall src/app/graphs/meal_analyze src/app/services/meal_analyze_workflow.py src/app/handlers/command_handlers
uv run pytest tests/unit/app/services/test_meal_analyze_workflow.py tests/unit/app/graphs/test_meal_analyze_graph_execution.py tests/unit/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py -q
```

## Next Steps

Proceed to Phase 4 after graph-enabled and graph-disabled behavior are both covered.
