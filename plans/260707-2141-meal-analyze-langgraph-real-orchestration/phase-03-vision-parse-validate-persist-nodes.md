---
phase: 3
title: "Vision Parse Validate Persist Nodes"
status: complete
priority: P1
effort: "1-2d"
dependencies: [2]
---

# Phase 3: Vision Parse Validate Persist Nodes

## Overview

Move the core meal analysis work into graph nodes: strategy selection, vision
analysis, nutrition parsing, optional FatSecret validation, meal persistence,
and cache invalidation.

## Context Links

- Vision service: `src/infra/adapters/vision_ai_service.py`
- Parser: `src/domain/parsers/vision_response_parser.py`
- Strategies: `src/domain/strategies/meal_analysis_strategy.py`
- Validation: `src/app/services/food_reference_validation_service.py`
- UoW port: `src/domain/ports/async_unit_of_work_port.py`
- Cache invalidation: `src/app/services/cache_invalidation_service.py`

## Requirements

- Functional: graph executes real `analyze_vision` and parser nodes.
- Functional: meal scans may run optional reference validation after parse.
- Functional: food-label scans parse `food_label_metadata` and skip reference
  validation.
- Functional: graph persists READY meal and invalidates caches before returning.
- Non-functional: provider ordering remains entirely inside `VisionAIService` and
  `AIModelManager`.

## Architecture

Target nodes:

```text
choose_analysis_strategy
 -> analyze_vision
 -> parse_nutrition
 -> maybe_validate_reference
 -> build_meal_domain
 -> persist_meal
 -> invalidate_cache
```

Conditional branches:

- `scan_mode == food_label` -> `FoodLabelImageAnalysisStrategy` and label parser.
- `scan_mode == meal_scan and user_description` -> user-context strategy.
- `fatsecret_validation_enabled == false` -> skip validation node.
- no-food/schema/parse errors -> return controlled exception, no persistence.

## Related Code Files

- Modify: `src/app/graphs/meal_analyze/nodes.py`
- Consider split: `src/app/graphs/meal_analyze/acquisition_nodes.py`
- Consider split: `src/app/graphs/meal_analyze/analysis_nodes.py`
- Consider split: `src/app/graphs/meal_analyze/persistence_nodes.py`
- Modify: `src/app/services/meal_analyze_workflow.py`
- Modify: upload and scan-by-url handlers to remove graph-enabled delegation to
  legacy handler methods.

## Tests Before

1. Graph node test: regular meal image calls `VisionAIService.analyze` or
   `analyze_with_strategy` as appropriate.
2. Graph node test: food-label path uses label strategy and label parser.
3. Graph integration test: valid meal persists and invalidates cache.
4. Failure test: no-food/schema validation does not persist.
5. Validation test: FatSecret runs only for meal scans when flag enabled.

## Refactor

Move duplicated orchestration logic out of handlers for graph-enabled path. Keep
small adapter methods only where legacy disabled path still needs them.

Recommended endpoint after this phase:

```python
if graph_enabled:
    return await workflow.run_uploaded(command)
return await self._handle_parallel_upload(command)
```

No graph-enabled call should delegate back to `_handle_parallel_upload` or
`_handle_legacy_scan_by_url`.

## Tests After

- Existing focused suites from prior plan still pass.
- New graph integration tests prove graph-enabled path no longer calls legacy
  handler callables.

## Implementation Steps

1. Add strategy-selection node.
2. Add vision-analysis node using `VisionAIServicePort`.
3. Add parse node with label/non-label branch.
4. Add validation node wired to existing `FoodReferenceValidationService`.
5. Add meal-builder/persistence node using `AsyncUnitOfWorkPort`.
6. Add cache invalidation node.
7. Remove graph-enabled legacy callable delegation.

## Success Criteria

- [x] Graph-enabled path has no legacy handler callable dependency.
- [x] Provider fallback logs still originate in `AIModelManager`.
- [x] READY/no-food behavior remains compatible.
- [x] Food-label behavior remains covered by graph integration tests.
- [x] Cache invalidation still happens before response.
- [x] Upload vision retry behavior preserves the existing fast-path attempt limit.

## Risk Assessment

- Risk: graph nodes start importing infrastructure directly.
- Mitigation: enforce architecture test: app graph may depend on ports/app
  services, not SQLAlchemy, SDK clients, or provider adapters.

- Risk: duplicating handler logic during migration.
- Mitigation: extract small app-layer helpers only when both upload and URL scan
  need the same behavior.
