---
phase: 2
title: "OpenAI Structured Translation Adapter"
status: completed
priority: P2
effort: 10h
dependencies: [1]
---

# Phase 2: OpenAI Structured Translation Adapter

## Context Links

- [Plan Overview](./plan.md)
- [Phase 1](./phase-01-neutral-translation-contract.md)
- [Approved Brainstorm](../reports/260809-1149-openai-translation-service-brainstorm.md)
- [Deep Scout](./reports/deep-scout-report.md)
- [Red-Team Adjudication](./reports/from-controller-to-planner-red-team-adjudication-proposal.md)

## Overview

Bind the new neutral translation port to OpenAI Responses API structured output.
Keep DeepL runtime alive beside it. No caller cutover yet. The adapter must
return sanitized `TranslationResult` values and low-cardinality metrics only.

## Key Insights

<!-- Updated: Red Team Session 1 - storage, metadata, and resource boundaries are explicit. -->
- Existing OpenAI structured output path already exists at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/providers/openai_provider.py:112-218` and `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/langchain_openai_adapter.py:37-266`.
- The LangChain schema normalizer strips keys like `minItems`, `maxItems`, `pattern`, and numeric bounds at `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/langchain_openai_adapter.py:231-266`; translation index invariants therefore need post-schema validation, not schema-only trust.
- Observability allowlists live in `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/observability_connectors.py:8-110`; translation metrics must stay inside those bounds.
- `OpenAIProvider.generate()` currently discards raw completion/refusal metadata after parsing, so Phase 2 needs an additive structured-result method rather than changing existing callers.
- The shared OpenAI storage flag can be enabled for other AI purposes; translation must override it with `store=False` because batches can contain user meal/search text.

## Requirements

<!-- Updated: Red Team Session 1 - accepted F03, F04, F06, and F08. -->
- Functional: add `OPENAI_TRANSLATION_MODEL` and `OPENAI_TRANSLATION_TIMEOUT_SECONDS=8.0`; reuse `OPENAI_API_KEY`, retry, and prompt-cache settings, but force translation invocations to `store=False` regardless of `OPENAI_STORE_RESPONSES`.
- Functional: send indexed JSON items, reconstruct ordered output by `index`, reject duplicate/unknown indexes, fill missing known items canonically and mark `PARTIAL`.
- Functional: add an additive structured-result envelope carrying parsed data plus bounded completion/refusal/incomplete classification and usage; keep existing `OpenAIProvider.generate()` return behavior unchanged.
- Functional: enforce Phase-1 input ceilings and reject any item whose output exceeds the greater of 256 UTF-8 bytes or four times its source bytes; preserve numbers, units, brands, and placeholders with post-parse semantic checks.
- Functional: map refusal, incomplete output, timeout/deadline, connection, 429, structural failure, or semantic-invariant failure to sanitized `UNAVAILABLE`/`PARTIAL` according to whether any safe known-index items remain.
- Non-functional: never log raw text, translated text, prompts, exception bodies, or provider payloads.

## Architecture

<!-- Updated: Red Team Session 1 - provider boundary and lifetime clarified. -->
Data flow:
`TextTranslationService -> TextTranslationPort -> OpenAITranslationAdapter -> OpenAIProvider.generate_structured_result(schema=..., store=False) -> OpenAILangChainAdapter.with_structured_output -> Responses API`

Message contract:
- Stable system instruction defines translation-only behavior and invariant rules.
- User-controlled strings appear only inside one indexed JSON user payload.
- Valid schema/index shape is necessary but not sufficient for `TRANSLATED`; resource and semantic invariants must also pass.

Backward compatibility path:
- DeepL files remain present.
- Phase 2 introduces a second provider implementation and tests it in isolation.
- Phase 3 will swap DI/callers to the neutral getter after this adapter is stable.

## Deep File Inventory

| Absolute path | Action | Test impact |
|---|---|---|
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/openai_translation_schemas.py` | Create | New schema + post-parse validator tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/openai_translation_failures.py` | Create | New failure-classification tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/openai_structured_generation_result.py` | Create | Sanitized parsed/status/refusal/usage envelope tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/adapters/openai_translation_adapter.py` | Create | New adapter characterization tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/config/settings.py` | Modify | Add `OPENAI_TRANSLATION_MODEL` and 8-second translation deadline; preserve other OpenAI defaults |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/.env.example` | Modify | Add translation-model and deadline envs; keep DeepL key until Phase 5 |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/providers/openai_provider.py` | Modify | Reuse prompt-cache/timeout plumbing for translation adapter |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/langchain_openai_adapter.py` | Modify | Add any helper exposure needed for translation structured-output tests only |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/observability_connectors.py` | Modify | Allowlist translation-safe metric/tag attributes |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/adapters/test_openai_translation_adapter.py` | Create | Failing-first adapter/outcome tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/services/ai/test_openai_translation_failures.py` | Create | Failing-first error classification tests |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/config/test_openai_translation_settings.py` | Create | Model/deadline defaults and overrides |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/services/ai/providers/test_openai_provider.py` | Modify | Guard prompt-cache/metric reuse for translation path |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/services/ai/test_langchain_openai_adapter.py` | Modify | Lock current schema-normalizer limits that force post-parse validation |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/monitoring/test_observability_facade.py` | Modify | Translation attributes remain tag-safe |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/monitoring/test_sentry_connector.py` | Modify | Sensitive translation payloads remain filtered |
| `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/adapters/test_ai_json_logging.py` | Modify | Translation observability keys stay allowlisted-only |

## Function/Interface Checklist

- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/providers/openai_provider.py:79-110` — current prompt-cache metrics path to reuse without duplicating provider plumbing.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/providers/openai_provider.py:112-159` — current structured-output request path that the adapter should call.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/providers/openai_provider.py:128-143` — current raw-result discard point; retain `generate()` and add a metadata-preserving method beside it.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/providers/openai_provider.py:205-218` — reusable error-code extraction for timeout/429/connection/status classification.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/langchain_openai_adapter.py:37-67` — strict structured-output invocation with raw message access.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/langchain_openai_adapter.py:135-159` — Responses API transport flags, timeout, retries, and `store` handling.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/services/ai/langchain_openai_adapter.py:231-266` — unsupported-schema-key stripping that forces adapter-side index validation.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/tests/unit/infra/services/ai/test_langchain_openai_adapter.py:326-349` — existing regression proving unsupported schema keys are removed.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/infra/config/settings.py:112-155` — current DeepL + OpenAI env surface to extend without removing DeepL yet.
- `/Users/alexnguyen/orca/workspaces/mealtrack_backend/bramble/src/observability_connectors.py:8-110` — low-cardinality key allowlists for metrics/log attributes.

## Dependency Map

<!-- Updated: Red Team Session 1 - dedicated translation provider ownership is intentional. -->
- Phase 1 neutral port/result types are required inputs.
- New adapter depends on `OpenAIProvider`, not `AIModelManager`, to avoid generic fallback chains.
- DI will own exactly one process-scoped translation adapter/provider instance, with an explicit reset seam for tests and no per-call client construction. This dedicated instance is intentional so `store=False` and the shorter deadline cannot drift with other AI purposes.
- `openai_translation_schemas.py` owns Pydantic request/response shapes; `openai_translation_failures.py` owns sanitized mapping to domain outcomes.
- Rollback boundary: remove the new adapter/schema/failure files and the new env setting; DeepL runtime still serves all callers.

## Tests Before

Expected red first after adding new assertions:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/infra/adapters/test_openai_translation_adapter.py \
  tests/unit/infra/services/ai/test_openai_translation_failures.py \
  tests/unit/infra/config/test_openai_translation_settings.py -q
```

Existing regressions expected green before edits:

```bash
uv run --python 3.13.2 pytest \
  tests/unit/infra/services/ai/providers/test_openai_provider.py \
  tests/unit/infra/services/ai/test_langchain_openai_adapter.py \
  tests/unit/infra/services/ai/test_openai_prompt_cache_policy.py \
  tests/unit/infra/monitoring/test_observability_facade.py \
  tests/unit/infra/adapters/test_ai_json_logging.py -q
```

## Refactor

<!-- Updated: Red Team Session 1 - structural success no longer grants translation success by itself. -->
1. Add translation-specific schema plus resource, index, output-expansion, and immutable-token validators.
2. Add the sanitized structured-result envelope and failure classifier without changing existing `generate()` callers.
3. Implement `OpenAITranslationAdapter` with fixed `store=False`, stable system/user separation, and adversarial fixtures.
4. Add `OPENAI_TRANSLATION_MODEL`, translation deadline, and observability allowlist keys without removing DeepL settings.

## Tests After

```bash
uv run --python 3.13.2 pytest \
  tests/unit/infra/adapters/test_openai_translation_adapter.py \
  tests/unit/infra/services/ai/test_openai_translation_failures.py \
  tests/unit/infra/config/test_openai_translation_settings.py \
  tests/unit/infra/services/ai/providers/test_openai_provider.py \
  tests/unit/infra/services/ai/test_langchain_openai_adapter.py \
  tests/unit/infra/monitoring/test_observability_facade.py \
  tests/unit/infra/monitoring/test_sentry_connector.py \
  tests/unit/infra/adapters/test_ai_json_logging.py -q

uv run --python 3.13.2 ruff check \
  src/infra/services/ai/openai_translation_schemas.py \
  src/infra/services/ai/openai_translation_failures.py \
  src/infra/services/ai/openai_structured_generation_result.py \
  src/infra/adapters/openai_translation_adapter.py \
  src/infra/config/settings.py \
  src/infra/services/ai/providers/openai_provider.py \
  src/infra/services/ai/langchain_openai_adapter.py \
  src/observability_connectors.py \
  tests/unit/infra/adapters/test_openai_translation_adapter.py \
  tests/unit/infra/services/ai/test_openai_translation_failures.py

uv run --python 3.13.2 mypy \
  src/infra/services/ai/openai_translation_schemas.py \
  src/infra/services/ai/openai_translation_failures.py \
  src/infra/services/ai/openai_structured_generation_result.py \
  src/infra/adapters/openai_translation_adapter.py \
  src/infra/config/settings.py \
  src/infra/services/ai/providers/openai_provider.py
```

## Regression Gate

```bash
uv run --python 3.13.2 lint-imports
uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries -q
```

## Test Scenario Matrix

| Scenario | Risk | Current coverage | Phase-2 target |
|---|---|---|---|
| Shuffled indexes reconstruct ordered output correctly | Critical | Missing | New adapter tests |
| Duplicate or unknown indexes reject whole batch | Critical | Missing | New adapter tests |
| Missing or empty known items become `PARTIAL` with canonical fill | High | Missing | New adapter tests |
| Timeout, 429, connection, refusal, incomplete output return sanitized unavailable | High | Partial via generic OpenAI tests only | New failure-classification tests |
| Translation metrics/tag attributes stay low-cardinality and payload-free | Medium | Generic AI observability tests | Updated observability tests |
| Global OpenAI storage enabled for another purpose | Critical | Shared transport only | Translation invocation still sends `store=False` |
| Oversized or instruction-like source text returns schema-valid poisoned output | Critical | Missing | Bounded request/output plus semantic-invariant and adversarial tests |
| Parsed output hides refusal/incomplete status | Critical | Current provider discards raw metadata | Additive envelope prevents `TRANSLATED` classification |

## Risk Assessment

- High: schema-only validation will miss index invariants. Mitigation: explicit post-parse validator.
- High: provider errors may leak raw payloads. Mitigation: classifier records only bounded error category + code.
- High: schema-valid output may still violate translation semantics. Mitigation: numeric/unit/placeholder preservation, output-expansion bounds, and reviewed adversarial cases.
- Medium: adding a new env setting can drift from existing OpenAI defaults. Mitigation: tests assert default model plumbing and prompt-cache reuse.

## Rollback

- Remove the new adapter/schema/failure files and `OPENAI_TRANSLATION_MODEL`.
- Keep all caller wiring on DeepL until Phase 3, so rollback is infra-only.

## Security Considerations

- Treat source strings as inert JSON data, never instructions.
- JSON separation reduces instruction ambiguity but does not prove semantic fidelity; only validated invariants plus evaluation may admit output.
- Force `store=False` at the translation invocation boundary.
- Do not log exception strings from provider SDK errors if they can include request metadata.
- Keep translation metrics bounded to provider/model/outcome/locale/batch bucket only.

## Doc Impact

- `.env.example` changes only. Evergreen provider docs still reference DeepL until Phase 5 removes runtime dependency.

## Todo

- [x] Add failing-first adapter and failure-classification tests.
- [x] Create translation schema + resource/index/semantic post-parse validators.
- [x] Add the sanitized structured-result metadata envelope without changing existing provider callers.
- [x] Create sanitized failure mapper.
- [x] Implement `OpenAITranslationAdapter`.
- [x] Add `OPENAI_TRANSLATION_MODEL`, translation deadline, forced `store=False`, and observability allowlist keys.

## Success Criteria

- [x] OpenAI translation adapter returns deterministic `TranslationResult` outcomes for every classified failure mode.
- [x] Structured-output index validation catches duplicates, unknowns, and short responses.
- [x] Translation cannot inherit provider storage and cannot classify bounded/semantic-invalid output as `TRANSLATED`.
- [x] Existing `OpenAIProvider.generate()` callers remain contract-compatible.
- [x] Observability tests prove no translation payload leaks into tags/context.
- [x] DeepL runtime still untouched for active callers.

## Next Steps

- Phase 3 can now move read-path callers to the neutral getter and outcome-aware cache admission.
- Do not delete any DeepL file or env key yet.
