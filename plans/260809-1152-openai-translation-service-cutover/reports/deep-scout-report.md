# OpenAI Translation Cutover Deep Scout Report

## Summary

Deep TDD inventory for the approved five-phase cutover. New neutral and OpenAI
components land additively before callers move. DeepL runtime deletion is last.
No unfinished plan functionally blocks this work, but several active plans share
`event_bus.py`, recommendation routes, and recommendation tests; implementation
must coordinate rather than run those edits concurrently.

## Locked Policies

- Exact languages: `en`, `vi`, `es`, `fr`, `de`, `ja`, `zh`.
- Any same-source/target pair is `PASSTHROUGH` without provider work.
- Unsupported source/target is canonical `UNAVAILABLE` without provider work.
- Only `TRANSLATED` is persistence/cache admissible.
- `PARTIAL` may render canonical-filled presentation output but is not cacheable.
- Unknown barcode source locale stays canonical. FatSecret responses requested in
  the target locale bypass translation. Translate only sources known to be English.
- Existing valid cached translations remain. No DB migration/backfill.
- Preserve migration/archive/completed-plan DeepL history.
- Run the domain-boundary class plus `lint-imports`; the complete layer-boundary
  file has a pre-existing stale service-count assertion.

## Phase 1: Neutral Translation Contract

Create:

- `src/domain/constants/languages.py`
- `src/domain/model/translation_result.py`
- `src/domain/ports/text_translation_port.py`
- `src/domain/services/translation/text_translation_service.py`
- Focused model/service/language-constant tests

Modify language duplicates in:

- `src/domain/constants/__init__.py`
- `src/domain/services/translation/__init__.py`
- `src/api/middleware/accept_language.py:16-18`
- `src/app/commands/user/update_language_command.py:8`
- `src/api/schemas/request/meal_requests.py:127`
- `src/domain/services/prompts/system_prompts.py:250,330`

Critical tests: cacheability by outcome; empty/same-language bypass; exception to
canonical unavailable; partial and wrong-length results; exact dedupe/expansion;
forward/reverse source-target forwarding; input immutability; seven-language
centralization. Leave current DeepL contract/wiring untouched in this phase.

## Phase 2: OpenAI Structured Translation Adapter

Create:

- `src/infra/services/ai/openai_translation_schemas.py`
- Sanitized structured-output failure classification under `src/infra/services/ai/`
- `src/infra/adapters/openai_translation_adapter.py`
- Adapter/settings tests

Modify:

- `src/infra/config/settings.py:135-154`
- `.env.example:96-102`
- `src/infra/services/ai/langchain_openai_adapter.py:61-67,178-231`
- `src/infra/services/ai/providers/openai_provider.py:79-159`
- `src/observability_connectors.py:8-51`
- Existing OpenAI provider/adapter/privacy tests

The adapter uses `OpenAIProvider` directly, never `AIModelManager`. Indexed JSON
items require post-schema validation because the existing schema normalizer strips
dynamic list/string/numeric constraints. Duplicate/unknown indexes reject the
whole batch. Missing/empty known items become partial. Refusal, incomplete output,
timeout, 429, connection, and schema failures become sanitized unavailable results.
Never log exception strings or raw text/provider data.

Critical tests: shuffled indexes; duplicates/unknowns; missing/empty items;
refusal/incomplete visibility; transient failures; prompt-injection-shaped data;
missing credentials; seven-language direction; model override; output-token and
low-cardinality metrics; privacy allowlists; Unicode/newline JSON round-trip.

## Phase 3: Read Path and Presentation Cutover

Create:

- `src/app/services/food_name_localizer.py`
- Focused food-localizer, search, barcode, parse, and DI tests

Modify:

- `src/api/base_dependencies.py`
- `src/api/dependencies/event_bus.py`
- `src/api/routes/v1/meal_recommendations.py`
- `src/app/services/catalog_meal_response_localizer.py`
- `src/app/handlers/query_handlers/search_foods_query_handler.py:120-194`
- `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:346-417`
- `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py:98-126`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py:318-348`
- Existing localizer/route/search/barcode/recognition/parse/DI tests

Catalog keeps its field allowlist and immutable projections. Search reverse
translation proceeds to English fallback only on `TRANSLATED`; forward output is
locale-cached only when all cache-bound text is translated or provider-native in
the target locale. Barcode persistence stays canonical and only the response is
projected. Ingredient and parse flows preserve nutrition/metadata and sanitize
payload-bearing logs. `TranslationResult` never crosses an API schema.

Critical tests: locale cache poisoning; exact bidirectional direction/order;
catalog shape under all outcomes; canonical barcode persistence; ingredient/parse
parent-flow success under all outcomes; neutral singleton identity; sentinel text
absent from logs.

## Phase 4: Persisted Meal and Suggestion Cutover

Modify/replace:

- `src/domain/model/meal/meal_translation_domain_models.py:46-75`
- `src/domain/services/meal_analysis/deepl_meal_translation_service.py:43-164`
- `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py`
- `src/domain/services/meal_suggestion/parallel_recipe_generator.py:554-580`
- `src/app/handlers/command_handlers/meal_suggestion/generate_meal_recipes_command_handler.py`
- `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- `src/app/graphs/meal_analyze/runtime.py` and `nodes.py:435-458`
- `src/app/handlers/command_handlers/meal_recommendation/log_recommended_meal_command_handler.py`
- `src/api/base_dependencies.py` and `src/api/dependencies/event_bus.py`
- Corresponding service, handler, graph, repository/UoW, and DI tests

Only a full translated outcome may save `MealTranslation`. Add instructionless
cache-completeness semantics based on expected source content. Preserve save/commit
before optional translation and repository/UoW ownership. Suggestions preserve
IDs, ordering, macros, quantities, and per-item degradation.

Missing critical coverage: no current test rejects partial/unavailable persistence;
no instructionless cache-complete case; no legacy scan translation-path test; no
non-English selected-recipe handler test; graph success path is under-covered.

## Phase 5: DeepL Removal and Release Verification

Delete after every caller uses neutral names:

- `src/domain/ports/deepl_translation_port.py`
- `src/domain/services/translation/deepl_text_translation_service.py`
- `src/domain/services/meal_analysis/deepl_meal_translation_service.py`
- `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py`
- `src/infra/adapters/deepl_translation_adapter.py`
- Replaced vendor-specific test modules

Remove active runtime/config/package residue from `src/`, `tests/`, `.env.example`,
`requirements.txt`, `pyproject.toml`, and `uv.lock`. Update
`docs/external-services.md` and `docs/runbooks/provider-outage.md`. Retain the
historical migration filename, archived docs, generated snapshots, and completed
plans. Add the reviewed seven-language evaluation fixture plus an optional,
credential-gated live smoke evaluation reported separately.

Final gates:

```bash
uv run --python 3.13.2 python -m compileall -q src
uv run --python 3.13.2 ruff format --check src/ tests/
uv run --python 3.13.2 ruff check src/ tests/
uv run --python 3.13.2 mypy src/
uv run --python 3.13.2 lint-imports
uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries -q
uv run --python 3.13.2 pytest tests/architecture/test_async_db_runtime_boundaries.py -q
uv run --python 3.13.2 pytest tests/unit --cov=src --cov-fail-under=65
```

Zero-runtime residue check targets active surfaces only. Historical residue gets a
separate expected-hit audit.

## Active Plan Coordination

- `260720-2133-meal-recommendation-ranking-v2`: overlaps recommendation route,
  event-bus composition, and recommendation tests; file overlap only.
- `260727-1905-slot-only-recommendation-replenishment`: overlaps event bus and
  recommendation tests; file overlap only.
- `260612-1046-service-initiated-bandwidth-reduction`: pending dead-code cleanup
  overlaps event bus and scan/upload handlers; independent, possibly stale.
- `260716-1509-four-table-meal-catalog-rework`: blocked plan has completed changes
  in the baseline; no new functional dependency.

## Unresolved Questions

None.
