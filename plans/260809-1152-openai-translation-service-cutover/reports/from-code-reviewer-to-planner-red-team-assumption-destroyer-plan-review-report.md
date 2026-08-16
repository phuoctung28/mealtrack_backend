# Assumption Destroyer Red-Team Plan Review

## Review Scope

- Plan: `plans/260809-1152-openai-translation-service-cutover/plan.md` and Phases 1-5.
- Approved input: `plans/reports/260809-1149-openai-translation-service-brainstorm.md`.
- Lens: hostile Assumption Destroyer.
- Verification role: Full-tier Scope Auditor.
- Method: read-only `rg`/file inspection. No lint, build, test, or production edit was run.
- Verdict: blocked. The plan cannot safely enter implementation with the critical barcode-cache contradiction and the unresolved suggestion-persistence/provider contracts below.

## Full-Tier Scope Audit

Seventy-five factual and scope claims were sampled: exactly 15 per phase.

| Phase | Checked | Verified | Failed | Unverified |
|---|---:|---:|---:|---:|
| 1 — Neutral contract | 15 | 12 | 2 | 1 |
| 2 — OpenAI adapter | 15 | 11 | 3 | 1 |
| 3 — Read paths | 15 | 11 | 3 | 1 |
| 4 — Persistence/suggestions | 15 | 11 | 3 | 1 |
| 5 — Removal/release | 15 | 12 | 2 | 1 |
| **Total** | **75** | **57** | **13** | **5** |

### Failed Claims

- Phase 1: the promised shared locale source does not cover all active seven-language policy copies. Additional translation-adjacent copies exist in `src/domain/services/prompts/prompt_constants.py:247-255`, `src/domain/services/meal_suggestion/parallel_recipe_generator.py:35-67`, and `src/domain/services/meal_value_insight_service.py:23-23`.
- Phase 1: the claimed known-source contract is not supplied by the existing forward interface, which accepts only texts and a target language at `src/domain/ports/deepl_translation_port.py:11-23`; parse-text currently substitutes an ASCII heuristic at `src/app/handlers/command_handlers/parse_meal_text_handler.py:312-327`.
- Phase 2: `OpenAIProvider.generate()` discards the raw structured response before returning at `src/infra/services/ai/providers/openai_provider.py:128-142`, so the planned adapter cannot inspect refusal/incomplete status through the architecture drawn in the phase.
- Phase 2: the provider records input and cached tokens only at `src/infra/services/ai/providers/openai_provider.py:79-110`; output-token usage required by the approved metrics cannot be recovered from its returned parsed dictionary.
- Phase 2: direct dependency on `OpenAIProvider` has no defined ownership. A process singleton already creates and owns an `OpenAIProvider` at `src/infra/services/ai/ai_model_manager.py:82-92` and `src/infra/services/ai/ai_model_manager.py:117-131`.
- Phase 3: FatSecret barcode data requested in the target locale is written to the global canonical table before response localization at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:109-124`; `food_reference` has no locale/provenance field at `src/infra/database/models/food_reference_model.py:28-36`.
- Phase 3: localized search caches a merge of provider-native results and unproven local rows without translating or classifying every field at `src/app/handlers/query_handlers/search_foods_query_handler.py:133-147`.
- Phase 3: the assertion that translation failure never fails search is false for the forward step: `translate_food_names()` is awaited outside the preceding exception boundary at `src/app/handlers/query_handlers/search_foods_query_handler.py:169-194`.
- Phase 4: suggestion translation returns bare `MealSuggestion` values and erases fallback/outcome identity at `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py:36-73`; orchestration then persists all values unconditionally at `src/domain/services/meal_suggestion/suggestion_orchestration_service.py:232-245`.
- Phase 4: `MealTranslation.is_fully_cached()` has no source-meal context with which to distinguish absent instructions from missing translations at `src/domain/model/meal/meal_translation_domain_models.py:61-75`.
- Phase 4: legacy short responses are padded with canonical strings and saved at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:94-105` and `src/domain/services/meal_analysis/deepl_meal_translation_service.py:138-148`; without provenance, those rows are indistinguishable from fully translated rows.
- Phase 5: the deletion inventory omits active DeepL residue in `src/api/mappers/meal_mapper.py:82-82`, `src/domain/model/meal/meal_translation_domain_models.py:69-75`, `src/domain/services/translation/__init__.py:1-3`, and `tests/unit/domain/services/test_meal_value_insight_service.py:116-116`.
- Phase 5: the zero-runtime grep excludes `.importlinter`, which retains a DeepL adapter architecture exception at `.importlinter:162-176`; stale ignores are explicitly tolerated by `unmatched_ignore_imports_alerting = none` at `.importlinter:27-35`, so `lint-imports` will not expose this miss.

### Unverified Claims

- Phase 1: immutability and exact `TranslationResult` shape are new code with no current artifact to verify.
- Phase 2: the new indexed translation schema/prompt and post-parse validator do not exist yet.
- Phase 3: the new `food_name_localizer` outcome-to-presentation contract does not exist yet.
- Phase 4: the intended outcome-aware meal/suggestion replacement contract is not specified at signature level.
- Phase 5: the seven-language fixture and live-smoke acceptance rubric do not exist yet.

### Instantiation and Lifetime Audit

| State/service | Current instantiation sites | Lifetime | Scope result |
|---|---|---|---|
| `Settings` | `get_settings()` constructs at `src/infra/config/settings.py:383-389`; tests construct isolated instances | Process-global in runtime | Verified. `OPENAI_TRANSLATION_MODEL` will be process config, but reset/override behavior must remain testable. |
| `AIModelManager` / current `OpenAIProvider` | Singleton creation at `src/infra/services/ai/ai_model_manager.py:82-103`; provider creation at `src/infra/services/ai/ai_model_manager.py:117-131` | Process-global | Failed. Phase 2 implies another direct provider owner without a shared factory or lifecycle rule. |
| Text translation service/adapter | Sole runtime construction at `src/api/base_dependencies.py:487-514` | Process-global; captured by both event buses and route dependencies | Failed contract. Missing-key and duplicate-provider initialization are unspecified for the replacement. |
| Meal translation service | Sole runtime construction at `src/api/base_dependencies.py:442-484` | Process-global service; fresh UoW per repository call via `src/infra/repositories/meal_translation_uow_adapter.py:15-25` | Verified lifetime, but cache-completeness state is under-specified. |
| Suggestion translation service | Sole runtime construction at `src/api/base_dependencies.py:370-398` | Process-global | Failed outcome boundary: fallback identity is not carried into the session-persistence layer. |
| Suggestion orchestration | Constructed by `src/api/base_dependencies.py:401-435`, then captured by the configured event bus | Effectively process-global | Failed persistence boundary: it unconditionally writes translated-or-canonical values. |
| Food-search/configured event buses | Globals at `src/api/dependencies/event_bus.py:221-222`, built at `src/api/dependencies/event_bus.py:234-318` and `src/api/dependencies/event_bus.py:321-336` | Process-global | Verified. Eager startup construction makes missing-key semantics a release-critical contract. |
| `MealAnalyzeRuntime` | Created by upload/scan handlers and declared at `src/app/graphs/meal_analyze/runtime.py:44-72` | Request/invocation-scoped container holding a process-global translation service reference | Verified; no request payload is added to the translation singleton by the plan. |
| Suggestion session | Domain lifetime documented at `src/domain/model/meal_suggestion/suggestion_session.py:10-22`; Redis TTL at `src/infra/repositories/meal_suggestion_repository.py:19-25` | Session-scoped, four hours | Existing language state is not serialized at `src/infra/repositories/meal_suggestion_repository.py:197-218`; do not add a second translation-locale state without selecting one authority. |

## Finding 1: Target-locale barcode names are already written into the canonical global cache

- **Severity:** Critical
- **Location:** Phase 3, sections "Requirements", "Architecture", and "Refactor" (canonical barcode cache; FatSecret target-locale bypass).
- **Flaw:** The plan simultaneously says FatSecret target-locale hits bypass translation and barcode persistence stays canonical. The current flow requests FatSecret with `query.language`, saves that localized name to `food_reference`, and only then calls response localization. `food_reference` is keyed globally by barcode and has no language/provenance column.
- **Failure scenario:** A Vietnamese request is the first scan for a barcode. FatSecret returns a Vietnamese name, which is persisted under the globally unique barcode. A later English request hits that row and returns it unchanged because English bypasses translation. The supposedly canonical table is now locale-poisoned, and the planned outcome gating cannot repair it because no translation result participated in the write.
- **Evidence:** Target-language FatSecret request and pre-response cache write are at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:109-124`; cache hits are returned through `_maybe_translate()` at `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:85-92`; the canonical table has one `name`, one unique `barcode`, and no locale at `src/infra/database/models/food_reference_model.py:28-36`.
- **Suggested fix:** Choose a canonical acquisition rule before implementation. With DB migration explicitly out of scope, fetch/store barcode provider data in English (or another proven canonical source) and create a separate target-locale response projection. Add a two-request test: non-English first, English second, asserting the stored row and English response remain canonical.

## Finding 2: Suggestion translation outcomes disappear before unconditional Redis persistence

- **Severity:** High
- **Location:** Phase 4, sections "Requirements", "Architecture", and "Refactor" (`TRANSLATED`-only suggestion persistence with per-item degradation).
- **Flaw:** The plan requires both per-item canonical fallback for presentation and `TRANSLATED`-only persistence, but it never defines an outcome-carrying suggestion contract. The existing service collapses success and fallback to the same `MealSuggestion` type; the generator repeats that erasure; orchestration persists every returned object.
- **Failure scenario:** Two recipes translate and one gets `UNAVAILABLE`. The failed item becomes its English original, the mixed list is returned as if homogeneous, and all three objects are serialized under the suggestion session. A later retrieval cannot tell that one item is canonical fallback, violating the locked cache-admission policy.
- **Evidence:** Per-item exceptions become bare originals at `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py:51-73`; `_translate_single()` again collapses failures to the original at `src/domain/services/meal_suggestion/parallel_recipe_generator.py:554-571`; all suggestions are persisted at `src/domain/services/meal_suggestion/suggestion_orchestration_service.py:232-245`; Redis serializes only payload fields, with no outcome/provenance, at `src/infra/repositories/meal_suggestion_repository.py:246-278`.
- **Suggested fix:** Specify an outcome-carrying aggregate such as `SuggestionTranslationResult(suggestion, outcome)` through translator, generator, streaming events, and orchestration. Keep display fallback separate from cache-admissible values, and test mixed batch outcomes for both returned data and Redis writes.

## Finding 3: The drawn provider call cannot observe refusal or incomplete-response state

- **Severity:** High
- **Location:** Phase 2, sections "Requirements", "Architecture", and "Function/Interface Checklist".
- **Flaw:** The plan says `OpenAITranslationAdapter -> OpenAIProvider.generate(schema=...)` and promises distinct refusal/incomplete classification. That method returns only parsed data. Its lower adapter has the raw message, but raises `parsing_error` before returning and exposes no typed refusal/incomplete envelope to `OpenAITranslationAdapter`.
- **Failure scenario:** Responses API returns an incomplete or refused structured response. LangChain produces a parsing error or missing parsed payload; `OpenAIProvider.generate()` propagates a generic error. The translation failure mapper cannot reliably classify refusal versus schema failure, and output-token/status telemetry is unavailable after raw response discard.
- **Evidence:** Raw and parsed values exist together only inside `OpenAILangChainAdapter.generate_structured()` at `src/infra/services/ai/langchain_openai_adapter.py:37-67`; `OpenAIProvider.generate()` records metrics and returns only `_dump_parsed(result.parsed)` at `src/infra/services/ai/providers/openai_provider.py:128-142`; current metrics extract input/cached tokens only at `src/infra/services/ai/providers/openai_provider.py:79-110`.
- **Suggested fix:** Define the provider API change explicitly before adapter work: return a typed structured-response envelope containing parsed payload, raw status/refusal/incomplete fields, and usage, or add a translation-specific provider method that maps those signals before discarding raw data. Enumerate compatibility for existing `generate()` callers rather than silently changing its return shape.

## Finding 4: Missing OpenAI credentials have no defined DI/startup behavior

- **Severity:** High
- **Location:** Phase 3, section "Backward compatibility path", and Phase 5, sections "Requirements" and "Safe Deletion Sequence".
- **Flaw:** Current translation DI explicitly returns `None` when `DEEPL_API_KEY` is absent. The plan rewires that getter, later deletes it, but never states what the neutral getter does when `OPENAI_API_KEY` is absent. Both event buses capture the translation service during eager process startup.
- **Failure scenario:** A worker starts without an OpenAI key in a degraded environment. If the new getter constructs `OpenAIProvider` with `None` or raises, eager event-bus initialization fails; startup swallows the exception, leaves buses uninitialized, and the first request retries construction and fails. This breaks the approved rule that translation unavailability must not fail parent flows.
- **Evidence:** Current optional behavior is at `src/api/base_dependencies.py:490-503`; food-search bus construction immediately calls and captures the getter at `src/api/dependencies/event_bus.py:248-274`; both buses are eagerly built at `src/api/main.py:241-254`; the existing OpenAI manager treats a missing key by omitting the provider at `src/infra/services/ai/ai_model_manager.py:117-130`.
- **Suggested fix:** Lock the neutral DI contract: absent key returns `None` and emits a bounded availability metric, unless the product explicitly chooses fail-fast. Add no-key startup tests for both event buses, direct recommendation dependencies, and Phase 5 after the old getter is deleted.

## Finding 5: The plan creates an undefined second process-wide OpenAI provider stack

- **Severity:** High
- **Location:** Phase 2, sections "Architecture" and "Dependency Map" (adapter depends directly on `OpenAIProvider`, not `AIModelManager`), plus Phase 3 DI rewiring.
- **Flaw:** There is already one process-global OpenAI provider owned by `AIModelManager`. No public provider factory/getter exists. Following the plan literally requires the translation getter to instantiate another `OpenAIProvider`, with another `OpenAILangChainAdapter` and per-model `ChatOpenAI` cache.
- **Failure scenario:** Text/vision traffic and translation traffic hold separate client/cache state, diverge under test reset or settings overrides, and double connection/resource ownership. A later model or storage-policy change updates one construction path but not the other. The plan has no shutdown/reset rule for the second stack.
- **Evidence:** `AIModelManager` is a locked process singleton at `src/infra/services/ai/ai_model_manager.py:82-103` and creates its OpenAI provider at `src/infra/services/ai/ai_model_manager.py:117-131`; `OpenAIProvider` constructs a new LangChain adapter at `src/infra/services/ai/providers/openai_provider.py:28-49`; that adapter owns mutable per-model client state at `src/infra/services/ai/langchain_openai_adapter.py:23-35` and `src/infra/services/ai/langchain_openai_adapter.py:135-147`.
- **Suggested fix:** Define one process-scoped provider factory/registry and let translation obtain the OpenAI provider directly without invoking fallback routing. Specify initialization, reset, and shutdown ownership. If a dedicated provider instance is intentional, document and test why duplicate client state is safe and how configuration parity is enforced.

## Finding 6: The privacy policy has multiple live leak sites but no complete verification gate

- **Severity:** High
- **Location:** Plan "Locked policies"; Phase 3 "Non-functional"/"Security Considerations"; Phase 4 "Security Considerations".
- **Flaw:** The plan bans raw text, translations, and provider exception bodies, yet its test inventory adds a logging test only for barcode. Active search, recognition, parse, meal persistence, and suggestion services log raw user/provider text or exception strings. General functional tests do not prove those payloads were removed.
- **Failure scenario:** A user searches or parses a sensitive meal description; the source query and translated text are logged. A provider exception embeds request metadata and is interpolated into logs. The cutover passes functional tests while retaining the exact data leak the locked policy forbids.
- **Evidence:** Search logs source and translated queries at `src/app/handlers/query_handlers/search_foods_query_handler.py:169-178`; recognition logs original and translated ingredient names plus raw exception strings at `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py:98-118`; parse logs food names/errors at `src/app/handlers/command_handlers/parse_meal_text_handler.py:286-306`; meal translation logs the translated dish and exception body at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:148-163`; suggestion translation logs exception bodies at `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py:36-84`.
- **Suggested fix:** Add explicit sentinel-capture logging tests for every modified caller/service, not only barcode. Replace payloads and exception strings with bounded outcome/error-class fields. Make these tests named release gates in Phases 3-5.

## Finding 7: The instructionless-cache fix cannot distinguish absence from legacy corruption

- **Severity:** High
- **Location:** Phase 4, sections "Key Insights", "Requirements", and Refactor step 1.
- **Flaw:** The plan directs `MealTranslation.is_fully_cached()` to accept legitimately instructionless meals, but the model has no source-meal shape, expected instruction count, or translation outcome. Existing code also padded short provider results with canonical input and saved them. Relaxing the predicate will bless both legitimate absence and polluted legacy rows.
- **Failure scenario:** A legacy non-English row contains a translated dish but canonical ingredient(s) from short-result padding and `meal_instruction=None`. After the planned predicate change, it is treated as complete and served forever. No backfill/provenance column exists to distinguish it from a legitimately instructionless, fully translated meal.
- **Evidence:** The domain object stores only translated fields and checks non-nullness at `src/domain/model/meal/meal_translation_domain_models.py:61-75`; source instructions are known only inside the service at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:80-96`; short results are canonically padded at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:98-105` and then saved at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:138-148`.
- **Suggested fix:** Move completeness evaluation to the meal service and pass explicit source expectations (instruction presence and expected ingredient count). Treat legacy ambiguous rows conservatively as misses and retranslate on demand. Do not implement this as a context-free relaxation of `is_fully_cached()`.

## Finding 8: Phase 5's “deep” deletion inventory and zero-residue command are incomplete

- **Severity:** High
- **Location:** Phase 5, sections "Deep File Inventory", "Safe Deletion Sequence", and "Tests After".
- **Flaw:** Active DeepL references exist outside the inventory, and the final grep omits an active architecture configuration file. The import-linter config deliberately tolerates unmatched stale ignores, so the listed layer gate remains green while a vendor-specific exception survives.
- **Failure scenario:** Implementation follows the file inventory, then discovers late failures in source/tests. After fixing those, the documented zero-runtime grep passes even though `.importlinter` still names `deepl_translation_adapter`. Release claims zero active residue while architectural configuration retains vendor debt.
- **Evidence:** Omitted active source references include `src/api/mappers/meal_mapper.py:82-82`, `src/domain/model/meal/meal_translation_domain_models.py:69-75`, and `src/domain/services/translation/__init__.py:1-3`; an omitted active test name exists at `tests/unit/domain/services/test_meal_value_insight_service.py:116-116`; `.importlinter` retains the adapter exception at `.importlinter:162-176`, and stale ignores do not alert at `.importlinter:27-35`.
- **Suggested fix:** Generate and freeze an explicit active-residue manifest from repository-wide `rg`, add `.importlinter` to Phase 5 changes and zero-residue grep, and document exclusions individually (migrations, archives, completed plans, generated `repomix-output.xml`) rather than limiting the scan to a hand-selected path list.

## Finding 9: Phase 1 does not actually establish one locale-policy authority

- **Severity:** Medium
- **Location:** Phase 1, sections "Key Insights", "Refactor", and "Success Criteria".
- **Flaw:** The plan enumerates four duplicates and then claims shared locale policy, but three active translation-adjacent maps/sets remain outside the phase. One recipe map even advertises many locales outside the approved seven, creating two incompatible definitions of “supported.”
- **Failure scenario:** A future locale change updates `languages.py`; middleware accepts it, while insights reject it or recipe prompt mapping silently falls back/accepts a different set. The cutover's source/target validation and prompt language names drift despite the “one source” success claim.
- **Evidence:** The exact seven-language mapping is duplicated at `src/domain/services/prompts/prompt_constants.py:247-255` and `src/domain/services/meal_value_insight_service.py:23-23`; recipe generation maintains a broader independent map at `src/domain/services/meal_suggestion/parallel_recipe_generator.py:35-67`; current boundary copies are also separate at `src/api/middleware/accept_language.py:16-18` and `src/app/commands/user/update_language_command.py:8-8`.
- **Suggested fix:** Inventory every translation-locale consumer and separate two concepts explicitly: the exact supported translation locale set, and a display-name map derived from that set. Keep intentionally narrower policies such as notifications separate and named as such. Add equality tests for every seven-language consumer.

## Finding 10: “Known source locale” is still an ASCII guess in parsed-meal localization

- **Severity:** Medium
- **Location:** Phase 3, sections "Requirements" and "Refactor" (translate only when source locale is known).
- **Flaw:** The plan never replaces parse-text's `_is_english()` heuristic. ASCII is a character property, not source-language provenance. The upstream prompt asks for bilingual output but model deviations are precisely the case this fallback handles.
- **Failure scenario:** The parser returns an unparenthesized ASCII Vietnamese, Spanish, brand, or transliterated name. `_is_english()` marks it English and the new adapter is called with `source=en`; OpenAI may rewrite a brand or mistranslate already-local text, contradicting the locked unknown-source fallback.
- **Evidence:** Source detection is `all(ord(c) < 128)` at `src/app/handlers/command_handlers/parse_meal_text_handler.py:312-327`, then the guessed names are translated at `src/app/handlers/command_handlers/parse_meal_text_handler.py:331-344`; the prompt only requests, rather than structurally guarantees, bilingual names at `src/domain/services/prompts/system_prompts.py:331-345`.
- **Suggested fix:** Carry explicit name-language/provenance in the structured parse contract, or translate only a structurally identified English component. If provenance is absent, preserve canonical text and return `UNAVAILABLE`; do not use ASCII as the source-language gate.

## Required Plan Corrections Before Implementation

1. Resolve canonical barcode acquisition and add the cross-locale first-writer test.
2. Specify outcome-carrying contracts for suggestion translation, persistence, and streaming.
3. Define a raw structured-response/provider contract that can classify refusal/incomplete and expose usage.
4. Define one OpenAI provider owner and missing-key startup semantics.
5. Redesign instructionless completeness using source expectations and legacy-row handling.
6. Expand privacy tests and the Phase 5 active-residue manifest/grep.
7. Complete locale-policy and source-provenance inventories.

## Unresolved Questions

- Is barcode canonical text required to be English, provider-native, or a source-specific value? The current schema cannot safely support “first request locale” as canonical.
- Should mixed-outcome suggestion batches be returned but never cached, or may individually `TRANSLATED` suggestions be cached while canonical fallbacks remain response-only?
- Is missing `OPENAI_API_KEY` a supported degraded production mode or a deployment-fatal configuration error? The approved parent-flow policy implies degraded mode, but the plan does not lock it.
- May legacy ambiguous `meal_translation` rows be retranslated on demand, or must every existing row remain trusted without provenance?

**Status:** DONE_WITH_CONCERNS
**Summary:** Full-tier hostile audit completed: 75 claims checked, 10 evidence-backed findings produced, and the plan is blocked by one Critical and seven High issues.
**Concerns/Blockers:** Canonical barcode cache poisoning, outcome-free suggestion persistence, provider signal/lifetime gaps, incomplete privacy gates, and unresolvable legacy cache completeness must be addressed before implementation.
