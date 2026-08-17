# Red-Team Failure-Mode Plan Review

## Scope and method

- Reviewed the overview, all five phase files, approved brainstorm, and deep-scout report in full.
- Read-only traced live translation entry points, guards, early returns, DI construction, provider calls, cache admission, database transactions, response projection, and rollback surfaces.
- Sampled 15 behavioral claims per phase (75 total). No lint, build, or tests run, per review instruction.

## Flow Tracer verification totals

| Phase | Sampled | Verified | Failed | Unverified | Failed/unverified causal claims |
|---|---:|---:|---:|---:|---|
| 1. Neutral contract | 15 | 13 | 1 | 1 | Failed: additive/no-runtime-effect claim conflicts with the Phase-3 shared getter design. Unverified: mixed empty/non-empty batch outcome and source-shaped completeness are not specified. |
| 2. OpenAI adapter | 15 | 11 | 3 | 1 | Failed: `OpenAIProvider.generate()` does not expose refusal/incomplete metadata; no translation-specific hard deadline; schema/index validity is treated as sufficient for persistence. Unverified: exact response-status field available through LangChain raw metadata. |
| 3. Read/presentation | 15 | 9 | 5 | 1 | Failed: shared getter also feeds write services; localized FatSecret barcode text is cached canonically; food-search local rows can be merged untranslated; cache rows lack language provenance; rollback is not response-only. Unverified: provider-native FatSecret output language guarantee. |
| 4. Persisted meal/suggestion | 15 | 8 | 6 | 1 | Failed: old padded rows remain cache hits; instructionless completeness lacks source context; post-commit translation blocks invalidation/response; rollback can retain bad rows; logging remains payload-bearing; check-then-save is not concurrency-safe. Unverified: operational request deadline relative to OpenAI retry duration. |
| 5. Removal/release | 15 | 10 | 3 | 2 | Failed: one-commit rollback cannot remove OpenAI-written cache/DB data; zero-runtime grep does not validate data provenance; fixture presence alone does not gate semantic acceptance. Unverified: live smoke credentials and an executable fixture evaluator/threshold. |
| **Total** | **75** | **51** | **18** | **6** | Release blocked by Findings 1-8. |

Representative full-tier traces:

- Read path: request -> language guard -> locale cache -> local database results -> localized FatSecret branch -> reverse translation branch -> forward localization -> locale cache -> response.
- Barcode: request -> language-specific FatSecret call -> canonical database upsert -> response localization; cache-hit early return skips any source-language verification.
- Meal write: meal save/commit -> synchronous translation with provider retry -> translation-row save/commit -> reload -> cache invalidation -> response.
- OpenAI: neutral service -> adapter -> `OpenAIProvider.generate(schema=...)` -> LangChain structured call -> raw message + parsed result -> provider discards raw -> adapter classification.
- Removal/rollback: neutral symbol rename -> DeepL deletion -> config/package deletion -> active grep -> deploy; rollback restores code but not provider-indistinguishable rows/cache entries written before failure detection.

## Finding 1: Phase 3 silently cuts Phase-4 write services over before they understand `TranslationResult`

- Severity: Critical
- Location: Phase 3, `Architecture / Backward compatibility path` (lines 41-50) and `Refactor` (lines 121-126); Phase 4, `Overview` (lines 20-24).
- Flaw: Phase 3 says it will change `get_deepl_text_translation_service` to return the neutral service while deferring persisted-meal and suggestion migration to Phase 4. That getter is shared by all three service families. The old meal and suggestion services consume `translate_texts()` as a list, whereas the new neutral contract returns `TranslationResult`.
- Failure scenario: Deploy Phase 3 independently. The first non-English meal or suggestion constructs its vendor-named wrapper around the neutral text service. Meal translation executes `len(translated)`, slicing, and indexing; suggestion translation does the same. The request fails/degrades after the plan claimed only presentation paths changed. Phase 3 is neither additive nor an independent rollback boundary.
- Evidence: `src/api/base_dependencies.py:383-395` constructs suggestion translation from the shared text getter; `src/api/base_dependencies.py:469-482` does the same for meal translation. The consumers require a list at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:98-129` and `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py:106-124`.
- Suggested fix: Keep the existing DeepL getter unchanged through Phase 3. Add a distinct neutral getter and migrate only read callers to it. Cut meal/suggestion wrappers to the result contract before repointing their dependencies, or declare Phases 3-4 one atomic, non-independently-deployable change with a single rollback boundary.

## Finding 2: The “canonical barcode cache” persists target-locale FatSecret names globally

- Severity: Critical
- Location: Phase 3, `Requirements` (lines 34-39), `Refactor` step 3 (lines 123-126), and `Success Criteria` (lines 211-216).
- Flaw: The plan assumes FatSecret target-locale hits can bypass translation while barcode persistence stays canonical. Live code asks FatSecret for the request language and writes that result to the language-agnostic `food_reference` row before response localization. The table has no source-language field.
- Failure scenario: A Vietnamese user is first to scan a barcode. FatSecret returns a Vietnamese product name, which is upserted under the unique global barcode. A later English user hits that row; the English early return skips translation and serves Vietnamese. Every subsequent consumer also treats the localized value as canonical.
- Evidence: The handler passes `query.language` to FatSecret and then caches before returning at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:109-124`; cache hits return through `_maybe_translate` at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:85-92`, whose English guard returns unchanged at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:346-356`. `FoodReferenceModel` has one `name`, one unique `barcode`, and no language/provenance field at `src/infra/database/models/food_reference_model.py:23-35,53-60`; the upsert overwrites `name` at `src/infra/repositories/food_reference_repository_async.py:203-241`.
- Suggested fix: For non-English barcode requests, persist only an English/canonical provider fetch and keep target-locale FatSecret text in the response projection. If that extra fetch is unacceptable, do not cache the localized name in `food_reference`; add a regression that performs `vi` scan -> `en` cache hit for the same barcode.

## Finding 3: “Preserve existing valid translations” also preserves known poisoned rows forever

- Severity: Critical
- Location: Plan `Overview` and locked policies (lines 21-36); Phase 4, `Dependency Map` (lines 101-106) and `Rollback` (lines 218-221).
- Flaw: Current code intentionally pads a short provider response with original English and saves the row. Completeness checks only non-null fields, and all read projections trust any row for the requested language. The cutover changes admission for future writes but has no lazy validation, invalidation, or repair for already-polluted rows.
- Failure scenario: DeepL previously returned only the dish name. Ingredients and instructions were padded with English and persisted under `vi`. After cutover, `is_fully_cached()` returns true, OpenAI is never called, and all meal/detail/activity reads continue serving mixed-language content indefinitely. The “no backfill” decision cannot distinguish valid rows from this acknowledged invalid class.
- Evidence: Cache-hit early return occurs at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:67-78`; short output is padded and saved at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:98-148`. Completeness is only a non-null check at `src/domain/model/meal/meal_translation_domain_models.py:69-75`. The existing test explicitly blesses padded originals at `tests/unit/domain/services/test_deepl_meal_translation_service.py:210-230`. API and activity projections apply rows without provenance/outcome validation at `src/api/mappers/meal_mapper.py:217-250` and `src/app/handlers/query_handlers/get_daily_activities_query_handler.py:187-191`.
- Suggested fix: Add lazy source-shaped validation before accepting a legacy row. Treat rows with missing/count-mismatched fields or canonical-filled values as cache misses and repair them through OpenAI on demand. This preserves genuinely valid rows without a bulk backfill.

## Finding 4: Best-effort translation remains on the critical request path after the irreversible commit

- Severity: High
- Location: Phase 4, `Requirements` line 37 and `Architecture` lines 41-47.
- Flaw: “Translation stays best-effort after parent persistence” is not equivalent to preserving parent request success. Translation is awaited after the meal commit but before reload, cache invalidation, and response. The plan reuses a 20-second OpenAI timeout and one SDK retry, with no smaller translation deadline or cancellation isolation.
- Failure scenario: OpenAI stalls or rate-limits after the meal is committed. The gateway/client times out and retries, creating another meal while the first exists. Cancellation or worker termination can occur before cache invalidation, leaving stale activity caches. The parent operation succeeded in PostgreSQL but failed from the caller's perspective.
- Evidence: OpenAI timeout/retry defaults are `20` and `1` at `src/infra/config/settings.py:135-140`, passed to the SDK at `src/infra/services/ai/langchain_openai_adapter.py:135-146`. Upload commits at `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:305-306`, awaits translation at `:315-337`, and only then reloads/invalidates at `:339-345`. The graph has the same ordering at `src/app/graphs/meal_analyze/nodes.py:345-370`; recommended-meal logging translates before invalidation at `src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py:74-80`.
- Suggested fix: Move mandatory cache invalidation immediately after the parent commit and put translation behind a strict sub-deadline shorter than the request SLA. Prefer a durable after-commit job/outbox; canonical response is already an approved degradation. Add cancellation and upstream-timeout scenarios, not only provider exceptions.

## Finding 5: The instructionless-cache fix cannot be correct with the proposed method contract

- Severity: High
- Location: Phase 4, `Requirements` line 36, `Refactor` step 1 (line 141), and `Success Criteria` line 244.
- Flaw: `MealTranslation.is_fully_cached()` receives no source meal shape. It cannot distinguish “source had no instructions” from “source had instructions but translation is absent.” Merely allowing `meal_instruction is None` makes failed translations look complete.
- Failure scenario: A meal with real instructions has a legacy/partial row containing translated dish and ingredients but `meal_instruction=None`. The Phase-4 fix relaxes the non-null condition for instructionless meals. That row becomes a permanent cache hit, so instructions are never retried and the response silently falls back/mixes languages.
- Evidence: The no-argument method only inspects the translation row at `src/domain/model/meal/meal_translation_domain_models.py:69-75`. It is called before source instructions are normalized or counted at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:67-92`. The response mapper independently applies any available translated fields at `src/api/mappers/meal_mapper.py:217-250`.
- Suggested fix: Define completeness against a source manifest: expected instruction count, expected ingredient IDs/count, and whether each field exists in source. Normalize the source first, then call something like `is_complete_for(expected_manifest)`. Test both legitimate zero-instruction meals and missing translation for a meal that has instructions.

## Finding 6: The chosen OpenAI boundary discards the metadata needed to enforce refusal/incomplete semantics

- Severity: High
- Location: Phase 2, `Requirements` line 35 and `Architecture` lines 38-46.
- Flaw: The plan binds `OpenAITranslationAdapter` to `OpenAIProvider.generate(schema=...)` and promises refusal/incomplete classification. LangChain returns both parsed data and a raw message, but `OpenAIProvider.generate()` discards the raw message and returns only the parsed dict. The adapter cannot prove the response completed without refusal.
- Failure scenario: Responses API returns an incomplete/refused response with a syntactically parseable item array. The adapter sees only indexes/texts, labels it `PARTIAL` or even `TRANSLATED`, and presentation or persistence accepts content that policy required to be `UNAVAILABLE`.
- Evidence: LangChain preserves `raw_message` at `src/infra/services/ai/langchain_openai_adapter.py:37-67`. `OpenAIProvider.generate()` receives that object, records cache usage, then returns only `_dump_parsed(result.parsed)` at `src/infra/services/ai/providers/openai_provider.py:128-143`. No status/refusal value crosses the provider boundary.
- Suggested fix: Add an additive structured-generation method/result that returns validated parsed data plus bounded completion/refusal metadata. Require explicit completed/no-refusal state before index validation can produce `TRANSLATED`; do not change the existing generic `generate()` return shape.

## Finding 7: Rollback restores code, not provider-indistinguishable bad data

- Severity: Critical
- Location: Phase 5, `Dependency Map` rollback claim (line 108) and `Rollback` (lines 202-205).
- Flaw: The plan says one revert restores DeepL and no data rollback is needed. OpenAI translations overwrite the same `(meal_id, language)` rows and locale cache keys with no provider/model/version provenance. A schema-valid but semantically wrong OpenAI result survives code rollback and is preferred as a cache hit.
- Failure scenario: OpenAI produces fluent but wrong food names during rollout. All indexes are present, so rows/cache entries are admitted. Monitoring triggers rollback to DeepL. Reads continue returning the bad OpenAI values; DeepL is never invoked because those rows are complete, and operators cannot identify which provider wrote them.
- Evidence: Meal translation storage contains language/content/timestamps but no provider/model/outcome at `src/infra/database/models/meal/meal_translation_model.py:20-36`; updates overwrite the existing row at `src/infra/repositories/meal_translation_repository_async.py:33-55`. Search cache keys are only language + query at `src/app/handlers/query_handlers/search_foods_query_handler.py:53-60`. Meal reads apply the stored language row directly at `src/api/mappers/meal_mapper.py:217-250`.
- Suggested fix: Add an explicit operational rollback data plan before deletion: version the locale-cache namespace and retain the previous namespace for instant fallback; for DB rows, record provenance/version or at minimum record the cutover timestamp and provide a reviewed scoped cleanup/retranslation command. Keep the provider switch reversible until the observation window closes.

## Finding 8: Privacy policy has no end-to-end gate for existing payload-bearing logs

- Severity: High
- Location: Plan locked policy line 35; Phase 3 `Requirements` line 39; Phase 4 `Security Considerations` lines 223-226.
- Flaw: The plan states that raw text and translated payloads must never be logged, but its logging tests are concentrated on barcode and generic OpenAI observability. Multiple touched Phase-3/4 paths currently log source/translated food text or provider exception strings, and the phase test matrices do not require sentinel-log assertions for them.
- Failure scenario: Cutover succeeds functionally, but user meal/query text and SDK error bodies continue to reach production logs/Sentry. A provider exception can contain request metadata; the release grep and translation outcome tests still pass.
- Evidence: Search logs raw query and translation at `src/app/handlers/query_handlers/search_foods_query_handler.py:169-179`. Ingredient recognition logs the identified and translated name at `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py:98-118`. Meal persistence logs the translated dish and exception string at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:148-163`. Suggestion translation logs exception strings and generator meal text at `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py:42-69` and `src/domain/services/meal_suggestion/parallel_recipe_generator.py:554-570,600-602`.
- Suggested fix: Add sentinel payload/error-body log-capture tests for search, ingredient, parse, persisted meal, suggestion, upload, scan, graph, and recommendation logging. Require bounded fields only (`operation`, locale pair, outcome, exception class, hashed/internal ID); remove all exception-string and food-text interpolation before Phase 5.

## Unresolved questions

- Are Phases 3 and 4 intended to be independently deployed? The written additive/rollback claims say yes, but the shared getter makes that false.
- What is the production HTTP/gateway timeout relative to the worst-case OpenAI timeout plus retry/backoff?
- What operational mechanism will identify and remove OpenAI-written rows/cache entries during rollback without deleting valid legacy translations?

**Status:** DONE
**Summary:** Hostile review completed with 8 evidence-backed release blockers across DI sequencing, cache correctness, legacy data, async ordering, failure classification, rollback, and privacy.
**Concerns/Blockers:** Plan should not enter implementation until Findings 1, 2, 3, 4, 6, and 7 are resolved in the phase design and regression matrices.
