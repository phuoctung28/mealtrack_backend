---
phase: 3
title: "Read Path and Presentation Cutover"
status: completed
priority: P2
effort: 12h
dependencies: [1, 2]
---

# Phase 3: Read Path and Presentation Cutover

## Context Links

- [Plan Overview](./plan.md)
- [Phase 1](./phase-01-neutral-translation-contract.md)
- [Phase 2](./phase-02-openai-structured-translation-adapter.md)
- [Approved Brainstorm](../reports/260809-1149-openai-translation-service-brainstorm.md)
- [Deep Scout](./reports/deep-scout-report.md)
- [Red-Team Adjudication](./reports/from-controller-to-planner-red-team-adjudication-proposal.md)

## Overview

Cut presentation-only and cache-sensitive read paths over to the neutral
translation outcome model: catalog response localization, localized food search,
barcode response localization, ingredient recognition, and parsed-meal
localization. No persisted meal/suggestion writes yet.

## Key Insights

<!-- Updated: Red Team Session 1 - DI sequencing and canonical barcode acquisition corrected. -->
- Recommendation routes localize only on response construction at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_recommendations.py:73-76`, `184-191`, `239-245`, `291-297`, `334-340`, and `384-390`; no persistence changes are needed there.
- Search currently caches translated fallback results inside `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/search_foods_query_handler.py:169-194`; Phase 3 must prevent non-`TRANSLATED` output from entering locale cache keys.
- Barcode `_maybe_translate()` is response-only at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/lookup_barcode_query_handler.py:346-417`, but the earlier locale-aware provider acquisition is not canonical; preserve the projection split while fixing acquisition.
- The current text getter also constructs Phase-4 meal/suggestion services at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/base_dependencies.py:383-395,469-482`; replacing it in Phase 3 would break list-returning consumers. Add a distinct neutral getter and leave the DeepL getter unchanged.
- Barcode currently requests FatSecret in the request locale and persists the result globally before projection at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/lookup_barcode_query_handler.py:109-124`; Phase 3 must acquire English canonical data for storage.

## Requirements

<!-- Updated: Red Team Session 1 - partial presentation, cache admission, and source provenance reconciled. -->
- Functional: apply `TRANSLATED` output to presentation and locale caches; allow canonical-filled `PARTIAL` output in presentation only; `UNAVAILABLE`/`PASSTHROUGH` stays canonical and none of those three outcomes enters a non-English locale cache.
- Functional: fetch/persist barcode provider data in English canonical form, then translate the response when requested; unknown-source cached/Open Food Facts text stays canonical rather than being mislabeled English.
- Functional: non-English search acquires canonical English provider/local data and uses OpenAI for forward localization; only a full `TRANSLATED` outcome enters the non-English locale cache. Do not treat a requested provider locale as proof of output language.
- Functional: replace parse-text ASCII guessing with structurally identified English-name extraction; unknown provenance remains canonical.
- Functional: `TranslationResult` must stay inside app/domain boundaries; API response schemas still receive plain strings/dicts.
- Non-functional: preserve request success on translation failure; move OpenAI-localized search writes to a versioned cache namespace with hashed normalized query keys, leaving the pre-cutover namespace available for rollback; sanitize logs/metrics with sentinel tests.

## Architecture

<!-- Updated: Red Team Session 1 - Phase 3 is independently deployable. -->
Data flows:
- Recommendation route: `request.language -> localize_meal_recommendation_plan/slot -> food_name_localizer -> translation service -> localized response only`.
- Search: `query -> reverse translation when needed -> canonical English provider/local search -> OpenAI forward localization -> non-English cache admission only on TRANSLATED`.
- Barcode: `English provider acquisition -> global canonical persistence -> outcome-aware response projection only`.
- Ingredient/parse: `structurally known English text -> outcome-aware response projection only`; unknown provenance stays canonical.

Backward compatibility path:
- Add `get_text_translation_service` for neutral read callers. Keep `get_deepl_text_translation_service` and every Phase-4 consumer unchanged throughout Phase 3.
- Keep persistence and write-path translation out of scope until Phase 4.

## Deep File Inventory

| Absolute path | Action | Test impact |
|---|---|---|
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/services/food_name_localizer.py` | Create | New outcome-aware localizer tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/services/catalog_meal_response_localizer.py` | Modify | Existing route/localizer tests gain outcome-aware assertions |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/base_dependencies.py` | Modify | Add distinct neutral getter while leaving DeepL getter unchanged |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/dependencies/event_bus.py` | Modify | Search/barcode/parse handler composition points to neutral behavior |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_recommendations.py` | Modify | Response localization stays shape-stable under all outcomes |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/search_foods_query_handler.py` | Modify | Locale-cache poisoning tests go red first |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/lookup_barcode_query_handler.py` | Modify | Canonical-cache vs localized-response tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/recognize_ingredient_command_handler.py` | Modify | Translation failure remains non-fatal and payload-safe |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/parse_meal_text_handler.py` | Modify | English-name translation fallback becomes outcome-aware |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/app/services/test_food_name_localizer.py` | Create | Failing-first localizer behavior tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/app/services/test_catalog_meal_response_localizer.py` | Modify | Allowlist + fallback outcome tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/query_handlers/test_search_foods_partial_cache.py` | Modify | Locale-cache admission and reverse-translation tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/query_handlers/test_search_foods_translation.py` | Create | Direction, English canonical acquisition, hash-key, bounds, and all-outcome tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py` | Modify | Canonical barcode cache invariants |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/query_handlers/test_lookup_barcode_translation.py` | Create | Non-English-first then English-read canonical persistence regression |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_logging.py` | Modify | No raw barcode or translation payload logs |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/command_handlers/test_recognize_ingredient_command_handler.py` | Modify | Non-English ingredient localization tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py` | Modify | Non-English parsed-meal localization tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/handlers/command_handlers/test_parse_meal_text_translation.py` | Create | Structural English provenance and four-outcome tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/api/test_meal_recommendations_route.py` | Modify | Route keeps compact/detail contracts under localization |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/api/test_event_bus_dependency_singletons.py` | Modify | Singleton wiring follows neutral read-path behavior |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/api/test_food_reference_dependency_wiring.py` | Modify | Getter wiring stays async-safe while behavior changes |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/api/test_translation_dependency_wiring.py` | Create | Neutral/DeepL getter identity and missing-key startup separation |

## Function/Interface Checklist

- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/services/catalog_meal_response_localizer.py:26-117` — current recommendation-plan and slot localization path; must stay presentation-only.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/search_foods_query_handler.py:42-118` — top-level search flow and metrics labels.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/search_foods_query_handler.py:120-194` — localized region search, reverse translation fallback, forward translation, and cache write path.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/lookup_barcode_query_handler.py:346-417` — translate response after canonical cache write, not before.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/recognize_ingredient_command_handler.py:103-118` — ingredient-name translation should degrade safely.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/parse_meal_text_handler.py:318-348` — remaining-English-name translation path to replace with outcome-aware behavior.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/dependencies/event_bus.py:248-315` — localized search/barcode composition root.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/dependencies/event_bus.py:505-525` — parse-text and search handler composition in the full event bus.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_recommendations.py:311-401` — plan + slot GET response localization surfaces.

## Dependency Map

<!-- Updated: Red Team Session 1 - distinct getter and fail-open lifecycle locked. -->
- `food_name_localizer.py` depends on Phase 1 result/outcome model and Phase 2 adapter behavior.
- Search, barcode, parse, and ingredient handlers consume the localizer; recommendation routes consume the updated catalog localizer.
- `get_text_translation_service` owns one process-scoped neutral adapter/provider and returns `None` when `OPENAI_API_KEY` is absent; eager event-bus startup and every parent flow must still succeed. Test reset clears only this singleton.
- The old DeepL getter remains a separate singleton until Phase 4 migrates its meal/suggestion consumers.
- Phase 4 write-path work depends on Phase 3 because suggestion and persisted meal flows reuse the same text service behavior.
- Rollback boundary: revert localizer usage and cache-admission logic only; canonical provider and persistence paths remain intact.

## Tests Before

Expected red first after adding outcome-aware assertions:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/app/services/test_food_name_localizer.py \
  tests/unit/app/services/test_catalog_meal_response_localizer.py \
  tests/unit/handlers/query_handlers/test_search_foods_partial_cache.py \
  tests/unit/handlers/query_handlers/test_search_foods_translation.py \
  tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py \
  tests/unit/handlers/query_handlers/test_lookup_barcode_translation.py \
  tests/unit/handlers/command_handlers/test_recognize_ingredient_command_handler.py \
  tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py \
  tests/unit/handlers/command_handlers/test_parse_meal_text_translation.py \
  tests/unit/api/test_translation_dependency_wiring.py \
  tests/unit/api/test_meal_recommendations_route.py -q
```

Existing regressions expected green before edits:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/app/services/test_catalog_meal_response_localizer.py \
  tests/unit/handlers/query_handlers/test_search_foods_partial_cache.py \
  tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_logging.py \
  tests/unit/api/test_meal_recommendations_route.py \
  tests/unit/api/test_event_bus_dependency_singletons.py -q
```

## Refactor

<!-- Updated: Red Team Session 1 - accepted F01, F02, F04, F07, F08, and F13. -->
1. Create `get_text_translation_service` beside the unchanged DeepL getter; prove missing-key startup degrades to `None` and no client is constructed per call.
2. Create `food_name_localizer.py` to convert `TranslationResult` into response-safe strings and explicit cache-admission decisions; render `PARTIAL` but never cache it.
3. Update search to reverse-translate only on `TRANSLATED`, acquire provider/local fallback in English, use cache namespace `food-search:v2` with hashed normalized query keys, and admit non-English cache output only on a full forward `TRANSLATED` result.
4. Change barcode acquisition to fetch/store English canonical data, then translate response fields; add the non-English-first/English-second regression.
5. Update ingredient and parse flows to translate structurally known English components only and remove ASCII source guessing.
6. Update recommendation presentation localization and add sentinel payload/error log tests across every Phase-3 caller.

## Tests After

```bash
uv run --python 3.13.2 pytest \
  tests/unit/app/services/test_food_name_localizer.py \
  tests/unit/app/services/test_catalog_meal_response_localizer.py \
  tests/unit/handlers/query_handlers/test_search_foods_partial_cache.py \
  tests/unit/handlers/query_handlers/test_search_foods_translation.py \
  tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py \
  tests/unit/handlers/query_handlers/test_lookup_barcode_translation.py \
  tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_logging.py \
  tests/unit/handlers/command_handlers/test_recognize_ingredient_command_handler.py \
  tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py \
  tests/unit/handlers/command_handlers/test_parse_meal_text_translation.py \
  tests/unit/api/test_meal_recommendations_route.py \
  tests/unit/api/test_event_bus_dependency_singletons.py \
  tests/unit/api/test_food_reference_dependency_wiring.py \
  tests/unit/api/test_translation_dependency_wiring.py -q

uv run --python 3.13.2 ruff check \
  src/app/services/food_name_localizer.py \
  src/app/services/catalog_meal_response_localizer.py \
  src/api/base_dependencies.py \
  src/api/dependencies/event_bus.py \
  src/api/routes/v1/meal_recommendations.py \
  src/app/handlers/query_handlers/search_foods_query_handler.py \
  src/app/handlers/query_handlers/lookup_barcode_query_handler.py \
  src/app/handlers/command_handlers/recognize_ingredient_command_handler.py \
  src/app/handlers/command_handlers/parse_meal_text_handler.py \
  tests/unit/app/services/test_food_name_localizer.py

uv run --python 3.13.2 mypy \
  src/app/services/food_name_localizer.py \
  src/app/services/catalog_meal_response_localizer.py \
  src/api/base_dependencies.py \
  src/api/dependencies/event_bus.py \
  src/app/handlers/query_handlers/search_foods_query_handler.py \
  src/app/handlers/query_handlers/lookup_barcode_query_handler.py \
  src/app/handlers/command_handlers/recognize_ingredient_command_handler.py \
  src/app/handlers/command_handlers/parse_meal_text_handler.py
```

## Regression Gate

```bash
uv run --python 3.13.2 lint-imports
uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries -q
uv run --python 3.13.2 pytest tests/architecture/test_async_db_runtime_boundaries.py::test_food_reference_request_dependencies_use_async_adapter -q
```

## Test Scenario Matrix

| Scenario | Risk | Current coverage | Phase-3 target |
|---|---|---|---|
| Localized search cache never stores `TranslationResult.PARTIAL`/canonical fallback under locale key | Critical | Existing “partial” test covers result count, not translation outcome | New outcome-aware search tests |
| Barcode cache stays canonical while response localizes | Critical | Logging/caching tests exist, translation split missing | New barcode async tests |
| Recommendation response contract survives unavailable/partial translation | High | Canonical and simple translation happy path only | Updated route/localizer tests |
| Ingredient and parsed-meal translation failures never fail parent flow | High | English-only path dominates | Updated handler tests |
| Neutral read-path wiring stays singleton-safe without aliasing | Medium | Existing singleton tests cover DeepL getter names | Updated DI tests |
| Search/recognition/parse/provider errors contain sentinel payloads | Critical | Active payload-bearing logs exist | Sentinel absent from every Phase-3 log capture |
| Missing OpenAI key during eager startup | Critical | DeepL-only optional behavior | Both event buses start and canonical parent flows succeed |

## Risk Assessment

- High: locale-cache poisoning changes search behavior. Mitigation: failing-first cache-admission tests before code changes.
- High: Phase-3 getter replacement would break list consumers. Mitigation: add a distinct neutral getter and assert old/new identities independently.
- High: recommendation route overlap with ranking-v2 plan. Mitigation: coordinate edits to `test_meal_recommendations_route.py` and `test_meal_recommendation_handlers.py`; do not parallelize.
- Medium: two temporary getters can confuse migration. Mitigation: explicit consumer-identity tests and removal only after Phase 4 is green.

## Rollback

- Revert localizer adoption and outcome-aware cache gating.
- Leave canonical search/barcode/provider paths intact so rollback is response-layer only.

## Security Considerations

- Keep source/translated text and exception strings out of logs; sentinel tests cover search, barcode, recognition, parse, and recommendation localization.
- Never let `TranslationResult` or provider metadata leak into API schemas or cache payloads.

## Doc Impact

- None in evergreen docs yet. Internal behavior only.

## Todo

- [x] Add failing-first `food_name_localizer` tests.
- [x] Update search cache-admission tests for translated-only locale keys.
- [x] Update barcode tests to prove canonical persistence and localized response split.
- [x] Add missing-key startup and distinct-getter identity tests.
- [x] Replace ASCII source guessing and add all-caller sentinel log tests.
- [x] Cut recommendation, parse, and ingredient paths to the neutral localizer.

## Success Criteria

- [x] Read-path callers use outcome-aware localization without changing response schemas.
- [x] Non-English locale caches admit full OpenAI `TRANSLATED` output only.
- [x] Barcode persistence remains canonical.
- [x] Partial presentation remains available without cache admission.
- [x] Missing OpenAI credentials do not prevent startup or parent-flow success.
- [x] `lint-imports`, `TestDomainLayerBoundaries`, and async food-reference boundary test stay green.

## Next Steps

- Phase 4 reuses the same localizer/text-service semantics for persisted meal and suggestion writes.
- Final DI symbol renames stay deferred to Phase 5 deletion pass.
