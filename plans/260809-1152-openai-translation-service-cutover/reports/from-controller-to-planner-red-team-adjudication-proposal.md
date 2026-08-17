# Red-Team Adjudication Proposal

Status: awaiting user review. No accepted finding has been applied to the plan yet.

Three reviewers produced 27 evidence-backed findings. Overlap was deduplicated
to 15 findings, capped per the red-team workflow.

## Proposed Dispositions

### 1. Phase-3 shared getter breaks Phase-4 consumers — Critical

- **Disposition:** Accept.
- **Evidence:** `src/api/base_dependencies.py:383-395,469-482` constructs the meal
  and suggestion services from the same DeepL text getter; those consumers still
  expect lists at `src/domain/services/meal_analysis/deepl_meal_translation_service.py:98-129`
  and `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py:106-124`.
- **Plan correction:** Add a separate neutral getter in Phase 3 and leave the
  DeepL getter unchanged until Phase 4 consumers understand `TranslationResult`.

### 2. Barcode locale poisons the global canonical row — Critical

- **Disposition:** Accept, modified.
- **Evidence:** `src/app/handlers/query_handlers/lookup_barcode_query_handler.py:109-124`
  requests FatSecret in the request locale and persists before response projection;
  `src/infra/database/models/food_reference_model.py:23-35,53-60` has one global
  name per barcode and no locale.
- **Plan correction:** Acquire and persist English canonical barcode data, then
  translate only the response. Locale-specific search results may be cached only
  under the requested locale when provider provenance is explicit; never write
  them into the global barcode row.

### 3. Translation may inherit provider-side response retention — Critical

- **Disposition:** Accept. This changes the approved reuse of the global storage flag.
- **Evidence:** `src/infra/config/settings.py:140-143`,
  `src/infra/services/ai/providers/openai_provider.py:39-49`, and
  `src/infra/services/ai/langchain_openai_adapter.py:149-159` pass the global
  storage setting through every shared OpenAI invocation.
- **Plan correction:** Translation must force `store=False` and prove it with an
  invocation-level test, even if other OpenAI purposes enable response storage.

### 4. Indexed JSON alone does not prevent prompt/cost abuse — Critical

- **Disposition:** Accept, modified.
- **Evidence:** Input becomes a `HumanMessage` at
  `src/infra/services/ai/langchain_openai_adapter.py:54-59`; search accepts an
  unbounded query and embeds it in a cache key at `src/api/routes/v1/foods.py:23-40`
  and `src/app/handlers/query_handlers/search_foods_query_handler.py:53-60`.
- **Plan correction:** Define system/user message separation, item-count and
  byte limits, output expansion limits, immutable-number/unit/placeholder checks,
  hashed cache keys, and adversarial semantic fixtures. Over-limit translation
  fails open canonically without changing the public response shape.

### 5. Suggestion outcomes disappear before Redis persistence — High

- **Disposition:** Accept.
- **Evidence:** Fallback becomes a plain suggestion at
  `src/domain/services/meal_suggestion/parallel_recipe_generator.py:554-571`, then
  every result is persisted at
  `src/domain/services/meal_suggestion/suggestion_orchestration_service.py:232-245`.
- **Plan correction:** Carry an internal suggestion-plus-outcome aggregate through
  generation and orchestration. For non-English sessions, partial/unavailable
  projections may be returned but must not be stored as translated suggestions.
  Canonical English suggestions remain valid canonical persistence.

### 6. Provider API discards refusal/incomplete metadata — High

- **Disposition:** Accept.
- **Evidence:** Raw metadata exists at
  `src/infra/services/ai/langchain_openai_adapter.py:37-67`, but
  `src/infra/services/ai/providers/openai_provider.py:128-143` returns only parsed data.
- **Plan correction:** Add an additive structured-result method/envelope for parsed
  content, bounded completion/refusal classification, and usage. Do not change
  the existing generic `generate()` return contract.

### 7. Payload-safe logging coverage is incomplete — High

- **Disposition:** Accept.
- **Evidence:** Payloads or exception strings are logged in
  `search_foods_query_handler.py:169-179`,
  `recognize_ingredient_command_handler.py:98-118`,
  `parse_meal_text_handler.py:286-306`,
  `deepl_meal_translation_service.py:148-163`, and
  `deepl_suggestion_translation_service.py:42-84`.
- **Plan correction:** Add sentinel log-capture tests for every migrated caller and
  service. Keep only bounded operation, locale, outcome, internal ID, and error class.

### 8. Missing-key and provider lifetime semantics are unspecified — High

- **Disposition:** Accept, modified.
- **Evidence:** Current DeepL DI returns `None` without a key at
  `src/api/base_dependencies.py:490-503`; eager event-bus construction occurs at
  `src/api/main.py:241-254`. `AIModelManager` already owns a separate OpenAI
  provider at `src/infra/services/ai/ai_model_manager.py:82-131`.
- **Plan correction:** Missing `OPENAI_API_KEY` is fail-open for translation and
  must not prevent startup. Use one dedicated process-scoped translation provider
  instance with explicit reset/test ownership; never construct clients per call.

### 9. Post-commit translation can still fail the client request — High

- **Disposition:** Accept, modified.
- **Evidence:** Upload commits, then awaits translation, then invalidates caches at
  `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py:305-345`;
  OpenAI defaults allow 20 seconds plus retry at `src/infra/config/settings.py:135-140`.
- **Plan correction:** Invalidate mandatory caches immediately after the parent
  commit, then run translation behind a shorter translation-specific deadline.
  Timeout returns the canonical response; no outbox/job is added in this scope.

### 10. Legacy completeness and rollback claims exceed available provenance — Critical

- **Disposition:** Accept, modified to preserve approved no-migration/no-backfill scope.
- **Evidence:** Completeness is context-free at
  `src/domain/model/meal/meal_translation_domain_models.py:69-75`; rows contain no
  provider/model provenance at
  `src/infra/database/models/meal/meal_translation_model.py:20-36`.
- **Plan correction:** Evaluate completeness against a source manifest, including
  expected instruction presence and ingredient count. Preserve structurally valid
  legacy rows. Add a rollout timestamp, version the search-cache namespace, and
  document scoped rollback cleanup for rows created/updated after cutover. Do not
  add schema, bulk backfill, or blanket existing-cache invalidation.
- **Residual risk:** A structurally complete legacy row containing canonical padded
  text cannot be distinguished perfectly without provenance; document this rather
  than silently reversing the approved data scope.

### 11. Meal translation uses check-then-insert under a unique constraint — High

- **Disposition:** Accept, modified.
- **Evidence:** Separate read/write UoWs and select-then-insert appear at
  `src/domain/services/meal_analysis/deepl_meal_translation_service.py:67-78,138-164`,
  `src/infra/repositories/meal_translation_uow_adapter.py:15-25`, and
  `src/infra/repositories/meal_translation_repository_async.py:33-60`.
- **Plan correction:** Make the repository write idempotent with the existing
  unique key, re-read the winner, and add concurrency coverage. Do not hold a
  database transaction open across the OpenAI call.

### 12. DeepL deletion manifest misses active residue — High

- **Disposition:** Accept.
- **Evidence:** Active references are also present in
  `src/api/mappers/meal_mapper.py:82`,
  `src/domain/services/translation/__init__.py:1-3`, and `.importlinter:162-176`.
- **Plan correction:** Build a repository-wide active-residue manifest, include
  `.importlinter`, and enumerate explicit history/generated exclusions.

### 13. Locale authority and parsed-name source detection are incomplete — High

- **Disposition:** Accept, modified.
- **Evidence:** The seven-language policy is duplicated in
  `src/domain/services/prompts/prompt_constants.py:247-255` and
  `src/domain/services/meal_value_insight_service.py:23,352-354`; parse-text uses
  ASCII as an English proxy at
  `src/app/handlers/command_handlers/parse_meal_text_handler.py:312-344`.
- **Plan correction:** Centralize the exact translation locale set while keeping
  intentionally broader prompt display-name maps separate. Translate parsed names
  only from a structurally identified English component; unknown provenance stays
  canonical.

### 14. Lock refresh can upgrade the OpenAI stack during cutover — Medium

- **Disposition:** Accept.
- **Evidence:** `pyproject.toml:45` permits a broad LangChain range while
  `uv.lock:1077-1088,1526-1543` pins the currently reviewed versions.
- **Plan correction:** Use a no-upgrade lock refresh and require a reviewed diff
  limited to DeepL removal and now-unused dependency metadata.

### 15. Client-controlled suggestion save is not translation-cache authorization — Critical

- **Disposition:** Reject.
- **Evidence:** `/v1/meal-suggestions/save` authenticates `user_id` and creates a
  new meal owned by that user at `src/api/routes/v1/meal_suggestions.py:226-285`
  and `src/app/handlers/command_handlers/meal_suggestion/save_meal_suggestion_command_handler.py:72-119`.
- **Rationale:** The body is intentionally an editable meal-creation payload. It
  does not write a localized translation row or authorize access to another user's
  resource. Binding it to a server suggestion record would be a separate product
  and API redesign, not a necessary OpenAI translation cutover control.

## Proposed Result

- 15 deduplicated findings: 6 Critical, 8 High, 1 Medium.
- 14 accepted (6 modified to stay within approved scope), 1 rejected.
- One explicit reversal requiring user approval: translation requests force
  provider response storage off instead of inheriting the global OpenAI setting.

## Unresolved Question

Approve the proposed dispositions and the `store=False` privacy change, or review
individual findings before the plan is edited?
