---
phase: 1
title: "Neutral Translation Contract"
status: completed
priority: P2
effort: 8h
dependencies: []
---

# Phase 1: Neutral Translation Contract

## Context Links

- [Plan Overview](./plan.md)
- [Approved Brainstorm](../reports/260809-1149-openai-translation-service-brainstorm.md)
- [Deep Scout](./reports/deep-scout-report.md)
- [Red-Team Adjudication](./reports/from-controller-to-planner-red-team-adjudication-proposal.md)

## Overview

Create the neutral language constants, translation outcome model, neutral port,
and neutral domain service. No runtime caller migration yet. DeepL wiring stays
live and unchanged behind the new contract.

## Key Insights

<!-- Updated: Red Team Session 1 - exact translation locale authority and source-provenance rules were tightened. -->
- Current contract is vendor-shaped at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/ports/deepl_translation_port.py:8-47` and `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/translation/deepl_text_translation_service.py:16-103`.
- Exact seven-locale translation policy is duplicated in `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/middleware/accept_language.py:16-18`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/commands/user/update_language_command.py:8`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/schemas/request/meal_requests.py:122-140`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/prompts/system_prompts.py:250-345`, `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/prompts/prompt_constants.py:247-255`, and `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_value_insight_service.py:23,352-354`.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_suggestion/parallel_recipe_generator.py:35-67` holds a broader display-name map that must stay explicitly separate from the exact translation-locale authority.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/parse_meal_text_handler.py:312-344` currently uses an ASCII heuristic as an English proxy; Phase 1 should lock the policy that unknown provenance remains canonical until a later phase provides structural source evidence.
- Phase 1 must not rename DI factories or delete DeepL classes. That belongs to later phases after characterization tests land.

## Requirements

<!-- Updated: Red Team Session 1 - locale authority and source-policy boundaries are now explicit. -->
- Functional: add neutral `TextTranslationPort`, `TextTranslationService`, shared translation locale constants, and a `TranslationResult` outcome model with `TRANSLATED`, `PARTIAL`, `PASSTHROUGH`, and `UNAVAILABLE`.
- Functional: same-language and empty-input requests bypass provider work; unsupported locale pairs normalize to `UNAVAILABLE`.
- Functional: define one exact translation-locale authority and helper predicates; intentionally broader display-name maps remain separate and explicitly named.
- Functional: define the source-provenance rule now: only structurally known English text is eligible for forward translation in later phases; unknown provenance must remain canonical.
- Functional: define provider-neutral input ceilings: at most 128 items, 4,096 UTF-8 bytes per non-empty item, and 32,768 UTF-8 bytes per batch. Over-limit input returns canonical `UNAVAILABLE` without calling the port.
- Non-functional: preserve input order, protect immutability, keep domain free of outer-layer imports, and do not add payload logging or runtime DI renames.

## Architecture

<!-- Updated: Red Team Session 1 - exact locale authority separated from broader display maps. -->
Data flow for this phase only:
`caller-facing tests -> TextTranslationService -> TextTranslationPort -> provider-specific implementation later`

Backward compatibility path:
- Keep `/src/domain/ports/deepl_translation_port.py` and `/src/domain/services/translation/deepl_text_translation_service.py` active.
- Add neutral files beside them.
- Centralize exact translation locale policy now so later phases stop duplicating acceptance/validation logic.
- Leave broader prompt/recipe display-name maps explicit; do not silently treat them as translation support lists.

## Deep File Inventory

<!-- Updated: Red Team Session 1 - locale-policy inventory now includes every live exact-translation consumer. -->
| Absolute path | Action | Test impact |
|---|---|---|
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/constants/languages.py` | Create | New unit coverage for locale set, normalization, and supported-pair checks |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/constants/translation_limits.py` | Create | Provider-neutral item/per-item/batch byte ceilings |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/model/translation_result.py` | Create | New unit coverage for outcome, cacheability, and canonical fallback |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/ports/text_translation_port.py` | Create | New domain-port contract tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/translation/text_translation_service.py` | Create | New tests for passthrough, unavailable, dedupe/expansion, and immutability |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/constants/__init__.py` | Modify | Export new language constants without breaking existing imports |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/translation/__init__.py` | Modify | Export neutral service additively |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/middleware/accept_language.py` | Modify | Middleware tests keep locale fallback green |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/commands/user/update_language_command.py` | Modify | User-language command validation aligns to one source |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/schemas/request/meal_requests.py` | Modify | Image-analysis language validator follows shared constants |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/prompts/system_prompts.py` | Modify | Prompt allowlist matches shared translation locale set |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/prompts/prompt_constants.py` | Modify | Exact seven-language translation constants stop drifting from prompt helpers |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_value_insight_service.py` | Modify | Insight-service language acceptance remains aligned to the exact translation set |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/constants/test_languages.py` | Create | Failing-first locale-centralization tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/constants/test_translation_limits.py` | Create | Boundary and no-provider-call limit tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/model/test_translation_result.py` | Create | Failing-first outcome/cacheability tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/translation/test_text_translation_service.py` | Create | Failing-first neutral-service behavior tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/domain/services/test_meal_value_insight_service.py` | Modify | Existing translation-locale assertions now point at shared constants |

## Function/Interface Checklist

- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/ports/deepl_translation_port.py:8-47` — current English-targeted, vendor-named port to mirror before any caller cutover.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/translation/deepl_text_translation_service.py:27-53` — current forward + reverse translation passthrough/fallback behavior to preserve behind the neutral service.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/translation/deepl_text_translation_service.py:55-103` — current `translate_food_names` dedupe + short-result padding behavior to characterize before Phase 3.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/middleware/accept_language.py:41-69` — locale parsing fallback contract that must use shared constants.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/api/schemas/request/meal_requests.py:122-140` — request-language validator to repoint at shared constants.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/prompts/system_prompts.py:250-345` and `/prompt_constants.py:247-255` — prompt locale validation and exact translation-locale copies to consolidate.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/domain/services/meal_value_insight_service.py:23,352-354` — additional exact-locale authority copy that must converge with the shared set.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/app/handlers/command_handlers/parse_meal_text_handler.py:312-344` — current ASCII source guess that later phases must stop trusting once this policy exists.

## Dependency Map

- New exact translation-locale authority: `languages.py` feeds middleware, request validation, prompt validators, and insight-service checks.
- New resource authority: `translation_limits.py` is enforced by the neutral service before any provider adapter runs.
- New domain translation surface: `translation_result.py` + `text_translation_port.py` + `text_translation_service.py`.
- Broader display-name maps remain separate by design; later phases must not silently widen translation support by importing them.
- Phase 1 outputs are blockers for Phase 2 adapter work and Phase 3 source-provenance handling.
- Rollback boundary: delete the new neutral files and revert constant exports only; no runtime DI, persistence, or API behavior changes yet.

## Tests Before

Expected red first after adding new assertions:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/domain/constants/test_languages.py \
  tests/unit/domain/constants/test_translation_limits.py \
  tests/unit/domain/model/test_translation_result.py \
  tests/unit/domain/services/translation/test_text_translation_service.py -q
```

Existing regressions expected green before edits:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/domain/services/translation/test_deepl_text_translation_service.py \
  tests/unit/domain/services/test_meal_value_insight_service.py \
  tests/unit/infra/adapters/test_deepl_translation_adapter.py -q
```

## Refactor

<!-- Updated: Red Team Session 1 - locale and provenance scope split is intentional. -->
1. Create neutral domain files and keep them additive.
2. Move exact supported-translation policy into `src/domain/constants/languages.py`.
3. Encode ordered-batch outcomes and cacheability in `TranslationResult`.
4. Enforce the 128-item, 4,096-byte item, and 32,768-byte batch limits before port invocation.
5. Repoint every live exact-translation locale consumer at the shared constants.
6. Keep broader display-name maps explicit and leave runtime DeepL wiring untouched.

## Tests After

```bash
uv run --python 3.13.2 pytest \
  tests/unit/domain/constants/test_languages.py \
  tests/unit/domain/constants/test_translation_limits.py \
  tests/unit/domain/model/test_translation_result.py \
  tests/unit/domain/services/translation/test_text_translation_service.py \
  tests/unit/domain/services/translation/test_deepl_text_translation_service.py \
  tests/unit/domain/services/test_meal_value_insight_service.py -q

uv run --python 3.13.2 ruff check \
  src/domain/constants/languages.py \
  src/domain/constants/translation_limits.py \
  src/domain/model/translation_result.py \
  src/domain/ports/text_translation_port.py \
  src/domain/services/translation/text_translation_service.py \
  src/domain/constants/__init__.py \
  src/domain/services/translation/__init__.py \
  src/api/middleware/accept_language.py \
  src/app/commands/user/update_language_command.py \
  src/api/schemas/request/meal_requests.py \
  src/domain/services/prompts/system_prompts.py \
  src/domain/services/prompts/prompt_constants.py \
  src/domain/services/meal_value_insight_service.py \
  tests/unit/domain/constants/test_languages.py \
  tests/unit/domain/constants/test_translation_limits.py \
  tests/unit/domain/model/test_translation_result.py \
  tests/unit/domain/services/translation/test_text_translation_service.py

uv run --python 3.13.2 mypy \
  src/domain/constants/languages.py \
  src/domain/constants/translation_limits.py \
  src/domain/model/translation_result.py \
  src/domain/ports/text_translation_port.py \
  src/domain/services/translation/text_translation_service.py \
  src/api/middleware/accept_language.py \
  src/app/commands/user/update_language_command.py \
  src/api/schemas/request/meal_requests.py \
  src/domain/services/prompts/system_prompts.py \
  src/domain/services/prompts/prompt_constants.py \
  src/domain/services/meal_value_insight_service.py
```

## Regression Gate

```bash
uv run --python 3.13.2 lint-imports
uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries -q
```

## Test Scenario Matrix

| Scenario | Risk | Current coverage | Phase-1 target |
|---|---|---|---|
| Same-language passthrough keeps provider cold | Critical | Only DeepL service covers `target_lang == "en"` | Neutral service test proves passthrough result + no port call |
| Unsupported source/target pair normalizes to unavailable | High | Missing | New neutral-service tests |
| Ordered dedupe and expansion preserve caller ordering | High | Covered only in DeepL food-name path | New neutral-service tests |
| Exact translation locale set stays identical across middleware, requests, prompts, and insight service | High | Duplicated manually | Shared-constant tests + focused import edits |
| Broader recipe/prompt display-name maps remain separate from translation support | Medium | Implicit only | New tests/documentation assertions on exact-vs-display helpers |
| Input exceeds item/per-item/batch ceiling | Critical | Missing | Canonical `UNAVAILABLE`; fake port remains cold at exact boundaries |

## Risk Assessment

- High: over-renaming here would collide with later DI work. Mitigation: add neutral files only, no caller rename.
- High: silent locale widening would break the exact seven-language boundary. Mitigation: separate exact translation support from broader display maps and test both.
- Medium: source-provenance policy could be bypassed later by heuristics. Mitigation: lock the rule now that unknown provenance remains canonical.

## Rollback

- Revert new neutral files and shared-constant imports.
- Leave DeepL runtime untouched, so rollback does not require cache or data repair.

## Security Considerations

- Treat locale codes as validated data, not prompt text.
- Do not add any logging of raw source strings, translated strings, or provider exceptions with payload bodies.

## Doc Impact

- None in evergreen docs yet. Provider docs stay on DeepL until Phase 5 runtime removal is complete.

## Todo

- [x] Add failing-first neutral contract tests.
- [x] Create shared exact translation locale constants and helper predicates.
- [x] Create and enforce provider-neutral input ceilings before port work.
- [x] Create `TranslationResult` outcome model and cacheability rule.
- [x] Create `TextTranslationPort` and `TextTranslationService`.
- [x] Repoint every live exact-translation locale consumer to shared constants.

## Success Criteria

- [x] Neutral domain files exist and compile without changing runtime DI.
- [x] Shared exact translation locale policy replaces all known live duplicates.
- [x] New tests prove passthrough, unavailable, dedupe, expansion, and immutability behavior.
- [x] Boundary tests prove oversized input never reaches a provider.
- [x] `lint-imports` and `TestDomainLayerBoundaries` stay green.

## Next Steps

- Phase 2 may bind OpenAI to `TextTranslationPort`.
- Phase 3 may enforce the locked source-provenance rule without inventing new locale authorities.
- Do not start caller migration until these neutral tests are green and reviewed.
