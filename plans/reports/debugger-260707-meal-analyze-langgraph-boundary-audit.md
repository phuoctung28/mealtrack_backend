# Meal Analyze LangGraph Boundary Audit

## Executive Summary
- **Issue:** Audit changed meal-analyze LangGraph wrapper, optional FatSecret validation, and app-layer wiring.
- **Impact:** Graph wrapper itself looks legacy-safe. Main risk is config/docs promise optional validation rollout that is not actually wired.
- **Root cause:** `MealAnalyzeWorkflow` supports optional validation, but `get_configured_event_bus()` only passes the boolean flag and never constructs `FoodReferenceValidationService` or the FatSecret provider.
- **Status:** DONE_WITH_CONCERNS
- **Fix:** No code patch applied in this pass. Recommend wiring service/provider/timeout before relying on the FatSecret validation flags.

## Timeline
- 14:xx - Read README, codebase summary, changed files, targeted tests.
- 14:xx - Traced `graph_enabled=false` and `graph_enabled=true` paths through both handlers.
- 14:xx - Verified optional validation service behavior and composition-root wiring.
- 14:xx - Ran targeted unit + architecture suite: 34 passed.
- 14:xx - Probed live `get_configured_event_bus()` import path; hit existing Redis suggestion-store requirement, not a LangGraph import failure.

## Technical Analysis
### Finding 1
- `graph_enabled=false` remains legacy-compatible.
- Evidence:
  - Upload handler still rejects `scan_mode="food_label"` before any graph branch at [src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:340).
  - Upload handler falls straight to `_handle_parallel_upload()` when graph is off at [upload_meal_image_immediately_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:351).
  - Scan-by-url handler falls straight to `_handle_legacy_scan_by_url()` when graph is off at [scan_by_url_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/scan_by_url_command_handler.py:363).
  - Targeted behavior tests passed: `test_upload_graph_disabled_keeps_legacy_path`, `test_scan_by_url_graph_disabled_keeps_legacy_path`.

### Finding 2
- `graph_enabled=true` does not skip existing dependency checks, parser flow, persistence, translation, or cache invalidation.
- Evidence:
  - Both handlers validate required dependencies before graph delegation:
    - [upload_meal_image_immediately_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:348)
    - [scan_by_url_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/scan_by_url_command_handler.py:364)
  - `MealAnalyzeWorkflow` only calls `run_meal_analyze_graph(...)`, then awaits the legacy handler unchanged:
    - upload path [src/app/services/meal_analyze_workflow.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/meal_analyze_workflow.py:31)
    - scan-by-url path [meal_analyze_workflow.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/meal_analyze_workflow.py:50)
  - Actual persistence/cache behavior still lives inside legacy handlers, unchanged:
    - upload save/commit/cache at [upload_meal_image_immediately_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:296) and [upload_meal_image_immediately_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:335)
    - scan-by-url food-label save/cache at [scan_by_url_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/scan_by_url_command_handler.py:248) and [scan_by_url_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/scan_by_url_command_handler.py:258)
    - scan-by-url meal save/cache at [scan_by_url_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/scan_by_url_command_handler.py:317) and [scan_by_url_command_handler.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/scan_by_url_command_handler.py:353)
  - Food-label scans are explicitly excluded from post-create validation in workflow at [meal_analyze_workflow.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/meal_analyze_workflow.py:68).

### Finding 3
- Optional FatSecret validation is implemented as default-off and non-blocking, but the production composition root does not wire it, so enabling the flag currently does nothing.
- Evidence:
  - Workflow only validates when both conditions are true: flag enabled and validation service present at [meal_analyze_workflow.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/meal_analyze_workflow.py:73).
  - `FoodReferenceValidationService` is best-effort and swallows timeout/provider failures at [src/app/services/food_reference_validation_service.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/food_reference_validation_service.py:27).
  - `get_configured_event_bus()` builds `MealAnalyzeWorkflow(fatsecret_validation_enabled=...)` but does not pass `food_reference_validation_service` at [src/api/dependencies/event_bus.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/dependencies/event_bus.py:320).
  - Runtime search shows no other production wiring for `FoodReferenceValidationService` or `FatSecretNutritionReferenceProvider`; they exist only as standalone classes/tests.
  - Docs currently imply real rollout control via `AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED` and timeout/version flags:
    - [docs/guides/meal-analyze-fastpath-rollout.md](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/guides/meal-analyze-fastpath-rollout.md:14)
    - [docs/system-architecture.md](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/system-architecture.md:115)

### Finding 4
- Two new settings are currently inert in runtime: `AI_MEAL_ANALYZE_EXTERNAL_PROVIDER_TIMEOUT_SECONDS` and `AI_MEAL_ANALYZE_GRAPH_VERSION`.
- Evidence:
  - Settings are declared at [src/infra/config/settings.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/config/settings.py:281).
  - Repo-wide usage search found them only in settings, docs, and the default-value test, not in runtime wiring.
  - `FoodReferenceValidationService` hardcodes its own default `timeout_seconds=5.0` at [food_reference_validation_service.py](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/services/food_reference_validation_service.py:21).
  - Graph nodes use `DEFAULT_GRAPH_VERSION = "v1"` and workflow never injects the setting.

### Eliminated Hypotheses
- No LangGraph-specific app import break found in targeted verification.
  - `tests/unit/architecture/test_meal_analyze_graph_boundaries.py` passed and confirms no `langgraph` in domain plus no provider SDK / SQL imports in graph files.
- No evidence that graph-enabled path bypasses legacy parser/persistence/cache behavior.
  - Wrapper delegates to existing handler methods without command mutation.
- No evidence that food-label scans get incorrectly routed into FatSecret validation.
  - Workflow returns immediately for `scan_mode="food_label"`.

## Verification Evidence
- Targeted suite passed:
  - `./.venv/bin/python -m pytest tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py tests/unit/app/services/test_meal_analyze_workflow.py tests/unit/app/services/test_food_reference_validation_service.py tests/unit/infra/adapters/test_fat_secret_service.py tests/unit/infra/adapters/test_fatsecret_nutrition_reference_provider.py tests/unit/handlers/command_handlers/test_upload_image_consistency.py tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py tests/unit/architecture/test_meal_analyze_graph_boundaries.py -q`
  - Result: `34 passed in 0.77s`
- Event-bus singleton test passed:
  - `./.venv/bin/python -m pytest tests/unit/api/test_event_bus_dependency_singletons.py -q`
  - Result: `3 passed in 0.96s`
- Direct `get_configured_event_bus()` probe failed on existing Redis suggestion-store requirement, not on LangGraph:
  - `RuntimeError: Redis suggestion session store not initialized...`

## Recommendations
### Immediate (P1)
- Wire `FoodReferenceValidationService` into `get_configured_event_bus()` with:
  - local food reference repository
  - `FatSecretNutritionReferenceProvider`
  - `timeout_seconds=settings.AI_MEAL_ANALYZE_EXTERNAL_PROVIDER_TIMEOUT_SECONDS`
- Until then, treat `AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED` as no-op and do not canary it.

### Short-term (P1)
- Either remove or wire `AI_MEAL_ANALYZE_GRAPH_VERSION`; current docs overstate runtime control.
- Add one composition-root test asserting that enabling the FatSecret flag results in a workflow with a non-`None` validation service.

### Long-term (P2)
- Add an integration-style test for graph-enabled upload + scan-by-url proving cache invalidation and persistence still happen through the legacy handler path.
- Consider emitting a metric/log when FatSecret validation is enabled but the validation service is absent; that would surface no-op rollout state immediately.

## Unresolved Questions
- Was the missing validation-service wiring intentional staging, or was the rollout guide updated ahead of the runtime composition root?
