---
phase: 4
title: "Persisted Meal and Suggestion Cutover"
status: completed
priority: P2
effort: 14h
dependencies: [2, 3]
---

# Phase 4: Persisted Meal and Suggestion Cutover

## Context Links

- [Plan Overview](./plan.md)
- [Phase 2](./phase-02-openai-structured-translation-adapter.md)
- [Phase 3](./phase-03-read-path-and-presentation-cutover.md)
- [Approved Brainstorm](../reports/260809-1149-openai-translation-service-brainstorm.md)
- [Deep Scout](./reports/deep-scout-report.md)
- [Red-Team Adjudication](./reports/from-controller-to-planner-red-team-adjudication-proposal.md)

## Overview

Move persisted meal translation and meal-suggestion generation/logging to the
neutral outcome model. This is the phase that stops partial/canonical fallback
from being stored under non-English translation rows or suggestion outputs.

## Key Insights

<!-- Updated: Red Team Session 1 - persistence outcomes, source shape, ordering, and races are explicit. -->
- `MealTranslation.is_fully_cached()` currently requires non-null instructions and ingredients at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/model/meal/meal_translation_domain_models.py:69-75`; meals with legitimately no instructions can never become cache-complete.
- `DeepLMealTranslationService.translate_meal()` currently pads short provider output and saves it at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_analysis/deepl_meal_translation_service.py:94-155`; that violates the approved `TRANSLATED`-only persistence rule.
- Upload, scan-by-url, graph, and recommended-meal logging all call persisted translation after the meal commit at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:315-337`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/scan_by_url_command_handler.py:336-355`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/graphs/meal_analyze/nodes.py:435-458`, and `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py:84-120`.
- Suggestion translation still uses vendor-named classes and per-item fallback at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py:36-133`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/parallel_recipe_generator.py:554-644`, and `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py:68-101`.
- Suggestion fallback is reduced to a plain `MealSuggestion` and later persisted unconditionally at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/suggestion_orchestration_service.py:232-245`; outcome must survive until cache admission.
- Current meal translation uses separate read/write UoWs and select-then-insert at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/repositories/meal_translation_repository_async.py:33-60`; the existing unique key needs idempotent conflict handling.

## Requirements

<!-- Updated: Red Team Session 1 - accepted F05, F07, F09, F10, and F11; F15 remains rejected. -->
- Functional: only `TRANSLATED` results may persist `meal_translation` rows or translated suggestion payloads.
- Functional: canonical English suggestions may persist as canonical session data; for non-English sessions, partial/unavailable presentation may be returned but cannot be stored as a successful localized suggestion.
- Functional: carry `SuggestionTranslationResult(suggestion, outcome)` through translation, concurrent generation, streaming projection, and orchestration cache admission; keep it internal to application/domain code.
- Functional: evaluate meal translation completeness against a source manifest (dish presence, ingredient IDs/count, instruction presence/count); legitimately instructionless meals can complete without treating missing required instructions as complete.
- Functional: preserve valid structurally complete legacy rows; no bulk invalidation/backfill or provider column. Record ambiguous legacy risk explicitly.
- Functional: after parent commit, perform mandatory cache invalidation before bounded best-effort translation; deadline/cancellation returns canonical response and does not reverse parent success.
- Functional: make `(meal_id, language)` persistence idempotent using the existing unique key and re-read the winner; never hold a DB transaction across the OpenAI call.
- Functional: suggestion flows preserve IDs, macros, quantities, units, durations, and ordering while degrading per-item to canonical output on unavailable translation.
- Non-functional: no raw text/error payload logging; add sentinel log-capture gates across meal/suggestion/upload/scan/graph/logging paths; no DI alias cleanup yet.
- Scope: do not redesign `/v1/meal-suggestions/save`; it is an authenticated user-owned editable meal-creation flow, not translation-cache authorization.

## Architecture

<!-- Updated: Red Team Session 1 - parent durability and localized-cache admission separated. -->
Data flows:
- Meal writes: `meal save + commit -> mandatory cache invalidation -> bounded optional translation -> idempotent translation-row write -> reload/response or canonical timeout fallback`.
- Graph path: `MealAnalyzeRuntime.meal_translation_service -> _translate_if_needed()` after persistence only.
- Recommendation logging: `materialize catalog meal -> save meal -> mandatory cache invalidation -> bounded optional request-language translation`.
- Suggestion generation: `generate English recipe -> translate to suggestion+outcome -> return translated/partial/canonical projection -> persist canonical English or fully translated localized artifacts only`.

Backward compatibility path:
- Keep vendor-named files through this phase.
- Swap internals to neutral `TranslationResult` semantics first.
- Delete names and symbols only in Phase 5 once every caller is migrated.

## Deep File Inventory

| Absolute path | Action | Test impact |
|---|---|---|
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/model/meal/meal_translation_domain_models.py` | Modify | New instructionless-cache completeness tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/model/meal_suggestion/suggestion_translation_result.py` | Create | Internal suggestion/outcome propagation tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_analysis/deepl_meal_translation_service.py` | Modify | New translated-only persistence tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py` | Modify | New translated-only batch outcome tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/parallel_recipe_generator.py` | Modify | Translation pipeline tests gain unavailable/partial cases |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/suggestion_orchestration_service.py` | Modify | Constructor typing and pipeline behavior stay aligned |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py` | Modify | Missing non-English selected-recipe coverage added |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_suggestions.py` | Modify | Name translation route uses neutral behavior without symbol deletion |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py` | Modify | Translation-after-commit and translated-only persistence tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/scan_by_url_command_handler.py` | Modify | Legacy scan translation-path tests added |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/graphs/meal_analyze/runtime.py` | Modify | Runtime typing stays explicit for graph translation dependency |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/graphs/meal_analyze/nodes.py` | Modify | Graph success + failure translation behavior tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py` | Modify | Request-language persistence rules stay non-fatal |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/base_dependencies.py` | Modify | Persisted meal/suggestion getters point to neutral internals |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/dependencies/event_bus.py` | Modify | Full event-bus composition stays singleton-safe |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/repositories/meal_translation_repository_async.py` | Modify | Idempotent existing-constraint upsert/re-read behavior |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/model/test_meal_translation.py` | Modify | Failing-first instructionless cache tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/test_deepl_meal_translation_service.py` | Modify | Failing-first no-partial-persist tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/test_deepl_suggestion_translation_service.py` | Modify | Failing-first translated-only suggestion tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py` | Modify | Per-item degradation tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py` | Modify | Missing non-English selected-recipe coverage |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/api/test_meal_suggestions_routes.py` | Modify | Suggestion-name translation route coverage |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py` | Modify | Translation only after commit and only translated persist path |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py` | Modify | Missing legacy scan translation-path coverage |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py` | Modify | Graph success-path translation gate |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/app/handlers/test_meal_recommendation_handlers.py` | Modify | Logging translation persistence semantics |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/api/test_event_bus_dependency_singletons.py` | Modify | Event-bus singleton wiring stays stable |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/api/test_food_reference_dependency_wiring.py` | Modify | Async meal-translation repository wiring guard stays green |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/repositories/test_meal_translation_repository_async.py` | Modify or create | Concurrent/idempotent write contract |

## Function/Interface Checklist

- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/model/meal/meal_translation_domain_models.py:69-75` — fix cache completeness semantics for instructionless meals.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_analysis/deepl_meal_translation_service.py:43-164` — replace short-result padding persistence with translated-only admission.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py:36-133` — move suggestion translation to neutral outcomes while keeping per-item degradation.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/parallel_recipe_generator.py:554-644` — keep pipeline concurrency and ordering while swapping translation semantics.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py:68-101` — selected recipe generation still translates after recipe generation only.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_suggestions.py:107-123` — discovery-name translation route remains presentation-only.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:315-337` — translation stays after parent commit.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/scan_by_url_command_handler.py:336-355` — legacy scan path translation remains non-fatal.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/graphs/meal_analyze/runtime.py:45-64` — runtime translation dependency remains per-invocation state, not shared mutable process state.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/graphs/meal_analyze/nodes.py:435-458` — graph translation trigger point after persistence.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py:84-120` — logging flow must never fail due to translation.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/base_dependencies.py:373-398`, `458-514` — suggestion, meal, and text translation composition points that must stay additive until Phase 5.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/dependencies/event_bus.py:416-446`, `620-626` — command-handler composition for meal write/log flows.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/repositories/meal_translation_repository_async.py:33-60` — replace check-then-insert failure behavior with idempotent conflict handling and winner re-read.

## Dependency Map

<!-- Updated: Red Team Session 1 - source manifest and outcome carrier are phase outputs. -->
- Phase 4 depends on Phase 2 adapter semantics and Phase 3 localizer/text-service behavior.
- Upload, scan, graph, logging, suggestion route, and recipe generation all converge on `base_dependencies.py` and `event_bus.py`; do not split them across parallel implementation tracks.
- Historical cached rows stay readable; only new persistence/cache admission rules change.
- Structurally complete legacy rows remain readable. Structurally ambiguous rows are cache misses evaluated against the source manifest; no bulk repair is performed.
- Phase 4 emits the internal suggestion outcome carrier and idempotent repository contract required before Phase 5 renames vendor files.
- Rollback boundary: revert translation admission rules while preserving meal/suggestion persistence ordering and canonical fallback behavior.

## Tests Before

Expected red first after adding translated-only persistence assertions:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/domain/model/test_meal_translation.py \
  tests/unit/domain/services/test_deepl_meal_translation_service.py \
  tests/unit/domain/services/test_deepl_suggestion_translation_service.py \
  tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py \
  tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py \
  tests/unit/api/test_meal_suggestions_routes.py \
  tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py \
  tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py \
  tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py \
  tests/unit/app/handlers/test_meal_recommendation_handlers.py \
  tests/unit/infra/repositories/test_meal_translation_repository_async.py -q
```

Existing regressions expected green before edits:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/domain/model/test_meal_translation.py \
  tests/unit/domain/services/test_deepl_meal_translation_service.py \
  tests/unit/domain/services/test_deepl_suggestion_translation_service.py \
  tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py \
  tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py \
  tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py \
  tests/unit/app/handlers/test_meal_recommendation_handlers.py -q
```

## Refactor

<!-- Updated: Red Team Session 1 - completeness is source-shaped and post-commit work is deadline-bounded. -->
1. Replace context-free completeness with `is_complete_for(source_manifest)` covering expected dish, ingredient IDs/count, and instruction presence/count.
2. Add the internal suggestion-plus-outcome carrier through translator, generator, streaming projection, and orchestration; persist localized suggestions only on `TRANSLATED`.
3. Change meal translation persistence to require `TRANSLATED` and make repository save idempotent on `(meal_id, language)` without spanning the provider call.
4. Move cache invalidation immediately after parent commit, then execute translation behind the Phase-2 deadline; timeout/cancellation returns canonical success.
5. Cut suggestion route and recipe generation over to neutral semantics, sanitize all touched logs, and retain the existing authenticated suggestion-save contract.

## Tests After

```bash
uv run --python 3.13.2 pytest \
  tests/unit/domain/model/test_meal_translation.py \
  tests/unit/domain/services/test_deepl_meal_translation_service.py \
  tests/unit/domain/services/test_deepl_suggestion_translation_service.py \
  tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py \
  tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py \
  tests/unit/api/test_meal_suggestions_routes.py \
  tests/unit/handlers/command_handlers/test_upload_fast_path_behavior.py \
  tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py \
  tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py \
  tests/unit/app/handlers/test_meal_recommendation_handlers.py \
  tests/unit/api/test_event_bus_dependency_singletons.py \
  tests/unit/api/test_food_reference_dependency_wiring.py \
  tests/unit/infra/repositories/test_meal_translation_repository_async.py -q

uv run --python 3.13.2 ruff check \
  src/domain/model/meal/meal_translation_domain_models.py \
  src/domain/model/meal_suggestion/suggestion_translation_result.py \
  src/domain/services/meal_analysis/deepl_meal_translation_service.py \
  src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py \
  src/domain/services/meal_suggestion/parallel_recipe_generator.py \
  src/domain/services/meal_suggestion/suggestion_orchestration_service.py \
  src/api/routes/v1/meal_suggestions.py \
  src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py \
  src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py \
  src/app/handlers/command_handlers/scan_by_url_command_handler.py \
  src/app/graphs/meal_analyze/runtime.py \
  src/app/graphs/meal_analyze/nodes.py \
  src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py \
  src/api/base_dependencies.py \
  src/api/dependencies/event_bus.py \
  src/infra/repositories/meal_translation_repository_async.py

uv run --python 3.13.2 mypy \
  src/domain/model/meal/meal_translation_domain_models.py \
  src/domain/model/meal_suggestion/suggestion_translation_result.py \
  src/domain/services/meal_analysis/deepl_meal_translation_service.py \
  src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py \
  src/domain/services/meal_suggestion/parallel_recipe_generator.py \
  src/domain/services/meal_suggestion/suggestion_orchestration_service.py \
  src/api/routes/v1/meal_suggestions.py \
  src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py \
  src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py \
  src/app/handlers/command_handlers/scan_by_url_command_handler.py \
  src/app/graphs/meal_analyze/runtime.py \
  src/app/graphs/meal_analyze/nodes.py \
  src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py \
  src/infra/repositories/meal_translation_repository_async.py
```

## Regression Gate

```bash
uv run --python 3.13.2 lint-imports
uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries -q
uv run --python 3.13.2 pytest tests/architecture/test_async_db_runtime_boundaries.py::test_meal_translation_dependency_uses_async_adapter -q
```

## Test Scenario Matrix

| Scenario | Risk | Current coverage | Phase-4 target |
|---|---|---|---|
| Partial/unavailable meal translation never persists | Critical | Current service tests bless short-result padding and save | Updated meal-translation tests |
| No-instruction meals can still become cache-complete | Critical | Missing | Updated domain-model tests |
| Upload/scan/graph/log flows keep parent success when translation is unavailable | High | Failure-only coverage exists; success gate incomplete | Updated handler + graph tests |
| Non-English selected recipes translate after generation without losing IDs/macros/order | High | Missing | Updated CQRS + route tests |
| Event-bus and base-dependency singletons still use async translation repo | Medium | Existing DI tests | Updated DI regression tests |
| Mixed suggestion outcomes enter Redis | Critical | Outcome is currently discarded | Only canonical English or `TRANSLATED` localized suggestions persist |
| Meal committed, translation stalls before invalidation/response | Critical | Current ordering awaits translation first | Invalidation completes first; deadline returns canonical success |
| Concurrent translation-row saves hit unique constraint | High | Check-then-insert | Idempotent write and winner re-read under concurrent calls |
| Sentinel meal/suggestion/provider text reaches logs | Critical | Active payload-bearing logs | Sentinel absent across every Phase-4 path |

## Risk Assessment

- High: persisted fallback pollution can silently poison translated rows. Mitigation: failing-first service tests and translated-only admission rules.
- High: legacy rows lack provider/outcome provenance. Mitigation: source-shaped structural validation, preserve valid rows, document ambiguity, and avoid claiming perfect legacy classification.
- High: post-commit provider latency can make durable writes look failed. Mitigation: invalidate first and enforce a shorter translation deadline with canonical success.
- Medium: concurrent misses can duplicate provider cost even with an idempotent DB write. Mitigation: guarantee data correctness now; do not hold DB locks across network calls or add distributed singleflight in this scope.
- High: `event_bus.py` overlaps the slot-replenishment plan. Mitigation: coordinate file lock; do not edit concurrently.
- Medium: graph runtime type drift can hide shared mutable state. Mitigation: keep translation dependency per-request and re-test graph scaffolding.

## Rollback

- Revert translated-only persistence logic and source-manifest completeness code.
- Parent meal/suggestion flows remain canonical and best-effort. Phase 5 owns the cutover-timestamp cleanup playbook for OpenAI-created/updated translation rows; do not claim code rollback alone restores data.

## Security Considerations

- Keep translation error logs bounded to internal `meal_id`, locale, outcome, operation, and exception class only.
- Sentinel tests must prove dish names, ingredients, recipe steps, translations, prompts, and exception bodies are absent from logs.

## Doc Impact

- None in evergreen docs yet. Phase 5 will update provider docs once DeepL runtime is actually gone.

## Todo

- [x] Add failing-first no-partial-persist tests for meals and suggestions.
- [x] Add source-manifest completeness tests for instructionless, required-instruction, ingredient-count, and ambiguous legacy rows.
- [x] Carry suggestion outcomes through orchestration and localized Redis admission.
- [x] Make meal-translation writes idempotent and add concurrency coverage.
- [x] Move invalidation before bounded post-commit translation in upload, scan, graph, and recommended-meal logging.
- [x] Add all-path sentinel privacy tests.
- [x] Add missing non-English selected-recipe and scan-by-url translation tests.
- [x] Keep DI additive; no symbol deletion.

## Success Criteria

- [x] Persisted meal translations save only on `TRANSLATED`.
- [x] Suggestion translation degrades per-item while localized persistence retains only `TRANSLATED` results.
- [x] Source-shaped completeness accepts legitimate instructionless meals and rejects missing required components.
- [x] Upload/scan/graph/log/request flows invalidate after the parent commit and remain successful on timeout, cancellation, or unavailable translation.
- [x] Concurrent translation writes produce one durable winner without an exposed integrity failure.

## Next Steps

- Phase 5 can delete DeepL files and rename residual vendor symbols only after these persistence tests are green.
- Preserve completed-plan and migration history during deletion.
