---
phase: 5
title: "DeepL Removal and Release Verification"
status: in-progress
priority: P2
effort: 10h
dependencies: [4]
---

# Phase 5: DeepL Removal and Release Verification

## Context Links

- [Plan Overview](./plan.md)
- [Phase 4](./phase-04-persisted-meal-and-suggestion-cutover.md)
- [Approved Brainstorm](../reports/260809-1149-openai-translation-service-brainstorm.md)
- [Deep Scout](./reports/deep-scout-report.md)
- [Red-Team Adjudication](./reports/from-controller-to-planner-red-team-adjudication-proposal.md)

## Overview

Delete DeepL runtime code, config, package refs, and vendor names after every
caller runs on the neutral OpenAI-backed path. Preserve history files. Finish
with release-grade verification, seven-language fixture review, and optional
credential-gated smoke coverage.

## Key Insights

<!-- Updated: Red Team Session 1 - residue, rollback data, and dependency-diff gates expanded. -->
- Active runtime/config residue is confirmed at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/config/settings.py:112-155`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/.env.example:126-129`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/requirements.txt:55`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/pyproject.toml:40`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/docs/external-services.md:25-51`, and `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/docs/runbooks/provider-outage.md:3-25`.
- Historical DeepL references must stay: `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/migrations/versions/051_add_deepl_json_columns_to_meal_translation.py:1-31`, completed plans under `/plans/`, and `docs/archive/**`.
- Full layer-boundary file still has a stale service-count assertion; release gates must use `lint-imports` plus `TestDomainLayerBoundaries`, not the entire file.
- Active residue also exists in `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/mappers/meal_mapper.py:82`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/translation/__init__.py:1-3`, and `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/.importlinter:162-176`; a hand-selected source list is not a sufficient zero-residue gate.
- Code rollback cannot identify OpenAI-written data because the schema has no provider provenance. Release must record a cutover timestamp and retain the pre-cutover search-cache namespace for scoped rollback without adding a migration.
- Deterministic translation admission protects numbers, placeholders, recognized locale units, and known brands; full semantic equivalence remains a provider-quality limitation rather than a lexical proof.
- Unit validation is green at 2231 passed / 44 warnings / 79.33% coverage; focused adapter, fixture, compile, mypy, and import-boundary checks pass.
- Release validation remains open: the repository-wide Ruff/format baseline is not green, and `tests/architecture/test_async_db_runtime_boundaries.py::test_repository_transaction_boundary_allowlist_does_not_expand` still fails on the pre-existing `src/infra/repositories/admin_meal_catalog_repository_async.py` allowlist mismatch.

## Requirements

<!-- Updated: Red Team Session 1 - accepted F10, F12, and F14. -->
- Functional: remove DeepL runtime imports, DI symbols, config keys, packages, and active tests from `src/`, `tests/`, env/config/package docs.
- Functional: rename remaining vendor symbols to neutral names in one pass; no transitional alias helpers left behind.
- Functional: add reviewed seven-language evaluation fixture and optional live OpenAI smoke boundary.
- Functional: freeze a repository-wide active DeepL residue manifest, including `.importlinter`, then remove every active hit while preserving enumerated migrations/archive/completed-plan/generated-history exclusions.
- Functional: record the deployment cutover timestamp and a reviewed rollback procedure that restores code, switches back to the retained pre-cutover search-cache namespace, and scopes deletion/retranslation of rows created or updated after cutover.
- Functional: refresh `uv.lock` without upgrading the reviewed LangChain/OpenAI stack and fail release if the lock diff exceeds DeepL removal, now-unused transitive metadata, and project metadata.
- Non-functional: preserve historical mentions in migrations, archives, and completed plans; keep release verification reproducible with exact commands.

## Architecture

<!-- Updated: Red Team Session 1 - deletion and rollback are separate gates. -->
Final runtime shape:
`caller -> TextTranslationService / MealTranslationService / SuggestionTranslationService -> TextTranslationPort -> OpenAITranslationAdapter -> OpenAIProvider`

Deletion rule:
- First create or rename neutral runtime files and move callers.
- Then delete vendor-named files and package/config residue.
- Finally run zero-runtime grep on active surfaces and separate historical-hit audit.
- Keep the Phase-3 versioned search-cache namespace boundary through an observation window; rollback selects the old namespace instead of trusting OpenAI-populated entries.
- Use existing row timestamps for a scoped operational cleanup/retranslation report; do not add provider/model columns or bulk backfill.

## Deep File Inventory

| Absolute path | Action | Test impact |
|---|---|---|
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_analysis/meal_translation_service.py` | Create or rename target | Neutral runtime replacement for vendor-named meal translation file |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/suggestion_translation_service.py` | Create or rename target | Neutral runtime replacement for vendor-named suggestion translation file |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/mappers/meal_mapper.py` | Modify | Remove vendor field/comments while preserving translation projection |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/translation/__init__.py` | Modify | Remove vendor exports |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/base_dependencies.py` | Modify | Rename getter symbols, remove `DEEPL_API_KEY` branches |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/dependencies/event_bus.py` | Modify | Final neutral handler composition |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_recommendations.py` | Modify | Replace `get_deepl_*` dependency usage |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_suggestions.py` | Modify | Replace `get_deepl_suggestion_translation_service` usage |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/search_foods_query_handler.py` | Modify | Remove vendor-class import names |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/lookup_barcode_query_handler.py` | Modify | Remove vendor-class import names |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/recognize_ingredient_command_handler.py` | Modify | Remove vendor-class import names |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/parse_meal_text_handler.py` | Modify | Remove vendor-class import names |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py` | Modify | Final neutral meal-translation type usage |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/scan_by_url_command_handler.py` | Modify | Final neutral meal-translation type usage |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/graphs/meal_analyze/runtime.py` | Modify | Replace `Any`-style translation dependency with neutral type if still pending |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/graphs/meal_analyze/nodes.py` | Modify | Neutral service usage only |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py` | Modify | Final neutral meal-translation type usage |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/suggestion_orchestration_service.py` | Modify | Remove vendor type names |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/parallel_recipe_generator.py` | Modify | Remove vendor type names |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/config/settings.py` | Modify | Remove `DEEPL_API_KEY`, keep `OPENAI_TRANSLATION_MODEL` |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/.env.example` | Modify | Remove DeepL section, keep OpenAI translation env |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/requirements.txt` | Modify | Remove `deepl==1.30.0` |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/pyproject.toml` | Modify | Remove `deepl==1.30.0` |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/uv.lock` | Modify | Remove resolved `deepl` entries |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/.importlinter` | Modify | Remove vendor-specific adapter ignore |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/docs/external-services.md` | Modify | Replace DeepL runtime doc with OpenAI translation ownership |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/docs/runbooks/provider-outage.md` | Modify | Replace DeepL outage row with OpenAI translation row |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/test_meal_translation_service.py` | Create or rename target | Neutral persisted meal translation tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/test_suggestion_translation_service.py` | Create or rename target | Neutral suggestion translation tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/fixtures/translation/openai_translation_eval_fixture.json` | Create | Reviewed seven-language fixture |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/integration/ai/test_openai_translation_smoke.py` | Create | Optional credential-gated live smoke |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/adapters/test_openai_translation_eval_fixture.py` | Create | Deterministic fixture schema, seven-language coverage, and invariant gate |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/ports/deepl_translation_port.py` | Delete | Vendor port removed after all callers move |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/translation/deepl_text_translation_service.py` | Delete | Vendor text service removed |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_analysis/deepl_meal_translation_service.py` | Delete | Vendor meal translation file removed |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py` | Delete | Vendor suggestion translation file removed |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/adapters/deepl_translation_adapter.py` | Delete | Vendor infra adapter removed |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/adapters/test_deepl_translation_adapter.py` | Delete | Vendor adapter tests replaced by neutral/OpenAI tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/translation/test_deepl_text_translation_service.py` | Delete | Vendor text service tests removed |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/test_deepl_meal_translation_service.py` | Delete after neutral replacement | Vendor meal translation test filename removed |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/test_deepl_suggestion_translation_service.py` | Delete after neutral replacement | Vendor suggestion translation test filename removed |

## Function/Interface Checklist

- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/base_dependencies.py:373-398`, `446-514` — current vendor-named getter surface to rename in one pass.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/dependencies/event_bus.py:248-315`, `416-446`, `505-525`, `620-626` — final caller composition points that must stop referencing vendor names.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_recommendations.py:73-76`, `165-166`, `222-223`, `275-276`, `321-322`, `367-368` — runtime route dependency usage to rename.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/routes/v1/meal_suggestions.py:107-123` — final runtime route call to vendor getter.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/query_handlers/search_foods_query_handler.py:14-16`, `/lookup_barcode_query_handler.py:17-18`, `/recognize_ingredient_command_handler.py:14-15`, `/parse_meal_text_handler.py:33-34` — vendor class imports to purge.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/suggestion_orchestration_service.py:22-24`, `61-72` and `/parallel_recipe_generator.py:16-18`, `83-99` — vendor suggestion translation types to purge.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/config/settings.py:112-155` — runtime config deletion boundary.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/.env.example:126-129` — env example deletion boundary.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/docs/external-services.md:25-51` and `/docs/runbooks/provider-outage.md:3-25` — provider documentation update surface.

## Dependency Map

<!-- Updated: Red Team Session 1 - rollback no longer claims code-only recovery. -->
- Phase 5 depends on all prior phases being green; otherwise deleting DeepL names will strand active callers.
- Shared-file coordination risk remains with recommendation-ranking-v2 (`meal_recommendations.py`, recommendation tests) and slot-only replenishment (`event_bus.py`).
- Historical artifact preservation is a hard constraint, not optional cleanup.
- Rollback boundary: one revert restores runtime files/package/config, while the recorded cutover timestamp and retained cache namespace drive a separate scoped data/cache recovery procedure.

## Safe Deletion Sequence

<!-- Updated: Red Team Session 1 - repository-wide residue and no-upgrade lock review are mandatory. -->
1. Create or rename neutral runtime replacements for any still-vendor-named service files.
2. Rename final caller symbols in `base_dependencies.py`, `event_bus.py`, routes, handlers, and suggestion services so no active import points at DeepL names.
3. Rename or recreate vendor-named test modules under neutral filenames, then delete old vendor-named test files.
4. Delete vendor runtime files: port, text service, meal translation service, suggestion translation service, adapter.
5. Remove `DEEPL_API_KEY`, `deepl` package refs, `.importlinter` vendor ignore, env example, and docs rows.
6. Refresh the lock without upgrades and inspect the lock diff before any other dependency change is accepted.
7. Run repository-wide zero-runtime grep with explicit history/generated exclusions, then run the expected historical residue audit.
8. Record the cutover timestamp, retained search-cache namespace, scoped translation-row cleanup query, and rollback owner in the provider-outage runbook.
9. Run deterministic fixture gates, full verification, and the optional live smoke/evaluation.

## Tests Before

Expected red first before deletion is complete:

```bash
rg -n "deepl|DeepL|DEEPL_API_KEY|get_deepl_|DeepL[A-Za-z]+Service|deepl_" \
  . --glob '!migrations/**' --glob '!docs/archive/**' --glob '!plans/**' \
  --glob '!repomix-output.xml' --glob '!.git/**'

uv run --python 3.13.2 pytest tests/integration/ai/test_openai_translation_smoke.py -o addopts='' -q
```

Existing regressions expected green before edits:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/domain/model/test_meal_translation.py \
  tests/unit/domain/services/meal_suggestion/test_parallel_recipe_generator_pipeline.py \
  tests/unit/app/handlers/test_meal_suggestion_cqrs_handlers.py \
  tests/unit/api/test_meal_suggestions_routes.py \
  tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py \
  tests/unit/app/handlers/test_meal_recommendation_handlers.py -q
```

## Refactor

1. Finish neutral file/symbol names everywhere active runtime still says DeepL.
2. Delete runtime DeepL modules and package/config/doc residue.
3. Add seven-language fixture and optional smoke boundary.
4. Prove zero-runtime residue without deleting historical references.

## Tests After

```bash
uv lock --offline
git diff -- pyproject.toml requirements.txt uv.lock

rg -n "deepl|DeepL|DEEPL_API_KEY|get_deepl_|DeepL[A-Za-z]+Service|deepl_" \
  . --glob '!migrations/**' --glob '!docs/archive/**' --glob '!docs/journals/**' \
  --glob '!plans/**' \
  --glob '!repomix-output.xml' --glob '!.git/**'

rg -n "deepl|DeepL|DEEPL_API_KEY|get_deepl_|DeepL[A-Za-z]+Service|deepl_" \
  migrations docs/archive docs/journals plans

uv run --python 3.13.2 python -m compileall -q src
uv run --python 3.13.2 ruff format --check src/ tests/
uv run --python 3.13.2 ruff check src/ tests/
uv run --python 3.13.2 mypy src/
uv run --python 3.13.2 lint-imports
uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries -q
uv run --python 3.13.2 pytest tests/architecture/test_async_db_runtime_boundaries.py -q
uv run --python 3.13.2 pytest tests/unit --cov=src --cov-fail-under=65
uv run --python 3.13.2 pytest tests/unit/infra/adapters/test_openai_translation_eval_fixture.py -q
uv run --python 3.13.2 pytest tests/integration/ai/test_openai_translation_smoke.py -o addopts='' -q
```

Interpretation:
- First grep must return no active-surface hits; planning journals are retained history.
- Second grep is expected to return hits only in migrations, archives, journals, and plans.
- Lock diff must not upgrade or otherwise change the resolved LangChain/OpenAI versions; any unrelated change requires a separate dependency review.
- Fixture test must cover all seven locales and every invariant. Live semantic results are reported separately and never hidden by a credential skip.
- Final smoke test must be skipped cleanly when credentials are absent and pass when credentials are present.

## Regression Gate

```bash
uv run --python 3.13.2 lint-imports
uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries -q
uv run --python 3.13.2 pytest tests/unit --cov=src --cov-fail-under=65
```

## Test Scenario Matrix

| Scenario | Risk | Current coverage | Phase-5 target |
|---|---|---|---|
| Active runtime grep has zero DeepL residue | Critical | Not true yet | Zero active hits |
| Historical grep keeps only approved residue | Critical | Not yet codified | Expected hits limited to migrations/archive/journals/plans |
| Full unit + lint + mypy + import boundaries stay green after deletion | High | Pre-delete only | Full release gate |
| Seven-language reviewed fixture captures semantic regressions | High | Missing | New fixture + review notes |
| Optional live smoke skips cleanly without creds and passes with creds | Medium | Missing | New integration smoke |
| `.importlinter` or omitted active file retains DeepL residue | Critical | Hand-selected grep misses it | Repository-wide manifest and zero-hit gate |
| Dependency removal upgrades LangChain/OpenAI | High | Lock refresh unconstrained | Offline/no-upgrade refresh plus reviewed lock diff |
| Rollback restores code but serves OpenAI-era cache/rows | Critical | No provenance columns | Retained cache namespace plus timestamp-scoped cleanup playbook |

## Risk Assessment

- High: deleting vendor names too early can strand callers. Mitigation: rename active callers first, delete last.
- High: package/doc cleanup can over-delete historical evidence. Mitigation: separate active-surface grep from historical-hit audit.
- High: `uv.lock` cleanup can silently upgrade the reviewed OpenAI stack. Mitigation: offline/no-upgrade refresh and allowlisted diff review.
- High: schema-valid but wrong OpenAI rows can survive a code rollback. Mitigation: record cutover time, keep the old search-cache namespace, and rehearse scoped cleanup; document that perfect provider attribution is unavailable without a schema change.

## Rollback

- Revert the Phase 5 commit to restore vendor files, package refs, env/docs rows, and test filenames.
- Switch search reads back to the retained pre-cutover cache namespace.
- Use the recorded cutover timestamp to list and review translation rows created/updated during the OpenAI window before scoped delete/retranslation. Do not claim code rollback alone repairs data.

## Security Considerations

- Live smoke must be credential-gated and must not print prompts, translations, or API keys.
- Fixture review artifacts should store only short canonical phrases, not sensitive user payloads.
- Rollback reports contain internal IDs/timestamps only, never meal text or translations.

## Doc Impact

- Update `docs/external-services.md` and `docs/runbooks/provider-outage.md`.
- Provider-outage runbook records cutover timestamp capture, cache namespace switch, scoped row audit/cleanup, and responsible operator.
- `.env.example` changes are required.
- Preserve historical docs and plans unchanged.

## Todo

- [x] Rename final active runtime symbols off DeepL names.
- [x] Delete DeepL runtime modules and packages.
- [x] Remove `DEEPL_API_KEY` docs/env/config references.
- [x] Add reviewed seven-language fixture and optional smoke test.
- [x] Remove `.importlinter` and all repository-wide active residue while preserving enumerated history.
- [x] Refresh the lock offline/no-upgrade and approve only the allowed dependency diff.
- [x] Record and rehearse the timestamp/cache-namespace rollback playbook.
- [x] Run deterministic fixture, zero-runtime grep, historical residue audit, and full release gates.

## Success Criteria

- [x] No DeepL runtime imports, config, packages, or active tests remain.
- [x] Historical DeepL references remain only in approved history surfaces.
- [x] LangChain/OpenAI resolved versions remain unchanged during DeepL removal unless separately reviewed.
- [x] Rollback can switch cache namespace and identify OpenAI-window rows without schema changes.
- [ ] Full release verification commands are green.
- [x] Optional live smoke is present and credential-gated.

## Next Steps

- Release only after the zero-runtime grep and full verification suite are green.
- Preserve completed-plan mentions; do not rewrite history artifacts for cosmetic cleanup.
