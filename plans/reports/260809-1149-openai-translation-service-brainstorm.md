---
title: OpenAI translation service brainstorm
type: brainstorm
status: approved
created: 2026-08-09
source: ck:brainstorm
---

# OpenAI Translation Service Brainstorm

## Summary

Replace DeepL runtime translation across all backend flows with an OpenAI
Responses API implementation. First neutralize provider-specific domain names,
then connect one dedicated OpenAI translation adapter. Preserve public API
contracts, valid cached translations, seven-language support, and canonical-text
degradation.

## Requirements

- Use OpenAI Responses API only. No DeepL runtime or fallback.
- Cover catalog responses, meal suggestions, persisted meal translations,
  bidirectional food search, barcode localization, ingredient recognition,
  parsed-meal localization, meal scans, and recommended-meal logging.
- Support `en`, `vi`, `es`, `fr`, `de`, `ja`, and `zh`.
- Preserve ordered batch behavior, public response shapes, IDs, quantities,
  units, nutrition, instruction durations, ranking, and persistence boundaries.
- English and empty input bypass provider calls.
- Provider failure returns canonical content and does not fail the parent flow.
- Fallback or partial content must not be persisted or locale-cached as a
  successful translation.
- Preserve valid existing cached translations. No backfill or database migration.
- Add independent `OPENAI_TRANSLATION_MODEL`, initially matching the current
  OpenAI text-model default.

## Existing Context

- Python 3.13 / FastAPI / Clean Architecture / CQRS backend.
- Current translation boundary is vendor-shaped:
  `DeepLTranslationPort` -> `DeepLTextTranslationService` -> DeepL adapter.
- DeepL names also appear in meal/suggestion services, dependency factories,
  handlers, routes, logs, tests, configuration, and dependencies.
- `OpenAIProvider` and `OpenAILangChainAdapter` already provide Responses API,
  strict Pydantic structured output, timeout/retry policy, storage control,
  prompt-cache support, and provider metrics.
- Catalog localization already uses a small structural translation protocol.
- Current swallowed provider errors can return unchanged English to meal
  persistence under a non-English cache key.

## Approaches Evaluated

| Approach | Advantages | Disadvantages | Decision |
|---|---|---|---|
| Replace adapter only, keep DeepL names | Small diff | Vendor debt remains throughout domain and composition | Reject |
| Neutral translation core plus dedicated OpenAI adapter | Explicit invariants, clean dependency inversion, easy future provider replacement | Broader internal rename and regression surface | Adopt |
| Add translation to `AIModelManager` | Reuses generic model routing and circuit breaker | Generic generation contract; possible non-OpenAI fallback; translation semantics obscured | Reject |

## Approved Architecture

```text
Callers
  -> TextTranslationService
  -> TextTranslationPort
  -> OpenAITranslationAdapter
  -> existing OpenAI structured-output stack
  -> Responses API
```

Use provider-neutral domain names:

- `TextTranslationPort`
- `TextTranslationService`
- `MealTranslationService`
- `SuggestionTranslationService`
- Neutral dependency factories such as `get_text_translation_service`

The translation operation accepts source language, target language, and an
ordered batch. It returns translated texts plus an outcome:

- `translated`: complete validated provider result
- `partial`: valid translated subset; missing items filled with originals
- `passthrough`: English-to-English or empty input
- `unavailable`: provider, refusal, timeout, or output-validation failure

Only `translated` may enter persistence or locale-specific caches. Presentation
flows may return `partial` or canonical fallback text.

## OpenAI Request Contract

Send user text as indexed JSON data. Require strict structured output with
`items[{index, text}]`. Treat input strings as data, never instructions.

Validate:

- Known indexes only, no duplicates
- Stable order reconstructed by index
- Missing entries filled with canonical input and marked `partial`
- Unknown or duplicate indexes reject the batch
- Empty output falls back for that item
- Refusal and incomplete output become `unavailable`
- Numbers, units, brands, placeholders, and recipe structure remain intact

Do not log source text, translated text, prompts, food payloads, or raw provider
responses.

## Configuration and Dependency Removal

- Add `OPENAI_TRANSLATION_MODEL`.
- Reuse `OPENAI_API_KEY`, request timeout, maximum retries, response-storage,
  and prompt-cache settings.
- Remove `DEEPL_API_KEY` from settings and `.env.example`.
- Remove the `deepl` package from dependency files.
- Remove DeepL adapter, vendor-named factories, comments, logs, and active tests.
- Preserve historical completed-plan references.

## Data and Cache Policy

- Existing valid cached translations remain readable.
- Cache misses use OpenAI.
- No provider/model provenance columns in this round.
- No offline regeneration or Batch API job.
- Persisted meal translations require a fully translated outcome.
- Locale-specific food-search caching requires a fully translated outcome.
- Meal cache completeness must treat legitimately absent instructions correctly.

## Verification

- Shared translation-result/service tests for all outcomes.
- OpenAI adapter tests for structured schema, exact index correlation, refusal,
  malformed output, timeouts, rate limits, and missing credentials.
- Forward and reverse translation coverage for all seven languages.
- Deduplication, order preservation, and partial-result coverage.
- Tests proving fallback output cannot enter persistence or localized caches.
- Existing catalog, suggestion, meal, search, barcode, recognition, parse-text,
  scan, and recommendation-log regression suites.
- Small reviewed seven-language food/recipe evaluation dataset.
- Optional credential-gated live OpenAI smoke evaluation, reported separately.
- CI-aligned unit suite, Ruff, and mypy.

## Success Metrics

- Zero DeepL runtime imports, package references, configuration, or DI symbols.
- All current translation flows resolve through the neutral service.
- No public API schema changes.
- Translation failures never fail parent meal/search/recommendation flows.
- No canonical or partial fallback stored under a non-English cache key.
- Low-cardinality metrics cover latency, outcome, source/target locale, batch-size
  bucket, token usage, and error category without payload content.
- Reviewed quality dataset passes the agreed semantic checks.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM output varies | Strict schema, indexed correlation, invariant validation, reviewed eval cases |
| Higher latency or cost | Deduplicate batches, separate model setting, measure tokens/latency before model changes |
| Prompt injection through food text | JSON data boundary and explicit instruction hierarchy |
| Rate limits or spend exhaustion | Existing bounded SDK retry policy; canonical fallback; safe outcome metrics |
| False localized cache entries | Outcome-aware persistence and cache admission |
| Broad rename breaks callers | TDD migration with focused call-site regressions before removal |

## Out of Scope

- Public translation HTTP endpoint
- DeepL fallback or shadow traffic
- Database schema changes
- Existing-cache invalidation or translation backfill
- New cross-request translation cache
- Model upgrade unrelated to translation migration
- Automated glossary management or fine-tuning

## Primary Touchpoints

- `src/domain/ports/deepl_translation_port.py`
- `src/domain/services/translation/deepl_text_translation_service.py`
- `src/domain/services/meal_analysis/deepl_meal_translation_service.py`
- `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py`
- `src/infra/adapters/deepl_translation_adapter.py`
- `src/infra/services/ai/`
- `src/api/base_dependencies.py`
- `src/api/dependencies/event_bus.py`
- Translation consumers under `src/api/`, `src/app/`, and `src/domain/`
- Corresponding `tests/unit/`, settings, environment example, dependency files,
  and evergreen external-service/API documentation

## Dependencies and Next Steps

1. Create a TDD implementation plan from this approved report.
2. Lock current translation behavior with focused tests.
3. Introduce neutral contracts and outcomes.
4. Add and validate the OpenAI adapter.
5. Migrate every caller and cache/persistence boundary.
6. Remove DeepL artifacts.
7. Run focused tests, full CI-aligned tests, Ruff, mypy, review, and docs sync.

## References

- OpenAI Structured Outputs: <https://developers.openai.com/api/docs/guides/structured-outputs>
- OpenAI Responses API: <https://developers.openai.com/api/reference/responses/overview>
- OpenAI model catalog: <https://developers.openai.com/api/docs/models>
- OpenAI prompt caching: <https://developers.openai.com/api/docs/guides/prompt-caching>
- OpenAI error codes: <https://developers.openai.com/api/docs/guides/error-codes>
- OpenAI Batch API: <https://developers.openai.com/api/docs/guides/batch>

## Unresolved Questions

None.
