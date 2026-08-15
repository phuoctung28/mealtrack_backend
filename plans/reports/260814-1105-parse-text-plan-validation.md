# Parse-Text Plan Validation

Date: 2026-08-14
Trigger: hard-mode post-red-team validation
Tier: Standard (Fact Checker + Contract Verifier)
Questions asked: 0; approved scope and accepted findings resolve all choices.

## Verification Results

- Claims checked: 30
- Verified: 30
- Failed: 0
- Unverified: 0

## Phase 1 Claims

1. VERIFIED — authenticated route exists and declares `ParseMealTextResponse`
   (`src/api/routes/v1/meals_manual_text.py:141`).
2. VERIFIED — guest route exists with the same response model
   (`src/api/routes/v1/meals_manual_text.py:185`).
3. VERIFIED — both routes construct `ParseMealTextCommand`
   (`src/api/routes/v1/meals_manual_text.py:162-167`, `:233-238`).
4. VERIFIED — the composition root registers one production handler
   (`src/api/dependencies/event_bus.py:505-513`).
5. VERIFIED — public response fields are defined by `ParseMealTextResponse`
   (`src/api/schemas/response/meal_responses.py:46-77`).
6. VERIFIED — the route mapper derives item calories from `MacrosModel` and
   forwards fiber/sugar defaults (`src/api/routes/v1/meals_route_helpers.py:23-39`).
7. VERIFIED — current AI schema repair is capped at two attempts
   (`src/app/handlers/command_handlers/parse_meal_text_handler.py:39-40`, `:143-187`).
8. VERIFIED — `current_items` is presently an unconstrained list of dictionaries
   (`src/api/schemas/request/meal_requests.py:14-26`).
9. VERIFIED — the handler sanitizes `text` before appending unsanitized serialized
   refinement data (`src/app/handlers/command_handlers/parse_meal_text_handler.py:63-75`).
10. VERIFIED — exhausted `AIOutputValidationError` maps to controlled HTTP 422
    (`src/api/exceptions.py:136-160`).

## Phase 2 Claims

1. VERIFIED — the provider port exposes staged candidate search and selected
   detail methods (`src/domain/ports/nutrition_reference_provider_port.py:6-24`).
2. VERIFIED — `FatSecretService.search_foods()` currently enriches every result,
   while staged methods already exist (`src/infra/adapters/fat_secret_service.py:189-283`).
3. VERIFIED — mapped details currently contain energy/P/C/F and units but omit
   fiber/sugar (`src/infra/adapters/fat_secret_service.py:345-366`).
4. VERIFIED — `NutritionResolver` currently scales a local in-memory candidate
   and has no production caller (`src/domain/services/nutrition_resolver.py:33-68`;
   repository usage search finds only its unit test constructions).
5. VERIFIED — the composition root already owns a batched normalized-reference
   closure (`src/api/dependencies/event_bus.py:395-405`).
6. VERIFIED — the canonical normalizer strips preparation qualifiers
   (`src/domain/services/meal_suggestion/ingredient_name_normalizer.py:10-16`, `:43-62`).
7. VERIFIED — `food_reference.name_normalized` is unique
   (`src/infra/database/models/food_reference_model.py:30-32`).
8. VERIFIED — the established trusted-reference validator uses a 110 g macro
   tolerance (`src/domain/services/meal_recommendation/ingredient_quantity_conversion_service.py:154-192`).
9. VERIFIED — `ParsedFoodItemDto` currently omits fiber/sugar, while the public
   response already exposes them (`src/app/schemas/meal_schemas.py:10-22`,
   `src/api/schemas/response/meal_responses.py:46-65`).
10. VERIFIED — constructor inventory is one production plus six direct handler
    unit constructions; shared staged methods also serve meal validation and the
    enriched wrapper (`src/api/dependencies/event_bus.py:505-513`,
    `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py:84-306`,
    `src/app/services/food_reference_validation_service.py:74-84`,
    `src/infra/adapters/fat_secret_service.py:189-228`).

## Phase 3 Claims

1. VERIFIED — the current prompt evaluator scores parser/schema/prompt behavior,
   not parse-text nutrition resolution (`src/domain/services/meal_analysis/prompt_eval_loop.py:26-219`).
2. VERIFIED — the existing development evaluator imports a domain loop rather
   than exercising HTTP routes (`scripts/development/evaluate_meal_analyze_prompt_candidates.py:15-105`).
3. VERIFIED — low-cardinality observability keys are allowlisted centrally
   (`src/observability_connectors.py:8-76`).
4. VERIFIED — current FatSecret transport timeout is 30 seconds
   (`src/infra/adapters/fat_secret_service.py:48-52`).
5. VERIFIED — parse-text currently adds a separate three-second per-item timeout
   (`src/app/handlers/command_handlers/parse_meal_text_handler.py:43-45`, `:268-271`).
6. VERIFIED — the internal response allows up to 20 items and the handler awaits
   lookups sequentially (`src/domain/model/ai/nutrition_contracts.py:278-288`,
   `src/app/handlers/command_handlers/parse_meal_text_handler.py:90-95`).
7. VERIFIED — central environment configuration defaults to development, so live
   mode must reject defaults rather than trust them (`src/infra/config/settings.py:17-22`).
8. VERIFIED — the repository has no existing parse-text evaluation CLI or corpus
   (target-path search returned no files before this plan).
9. VERIFIED — the documented CI-aligned unit command is
   `pytest tests/unit --cov=src --cov-fail-under=65`
   (`docs/testing-standards.md:1-7`).
10. VERIFIED — API mapping and guest lifecycle live outside the handler, so HTTP
    route tests are required for the public contract
    (`src/api/routes/v1/meals_manual_text.py:141-258`,
    `src/api/routes/v1/meals_route_helpers.py:23-39`).

## Confirmed Decisions

- Preserve the approved parse-text-only, response-compatible, no-RAG boundary.
- Treat preparation-aware matching, fiber propagation, request budgets, privacy,
  and staging controls as implementation requirements rather than open choices.
- Keep the unsigned-JWT guest limiter issue in a separate security investigation;
  this plan strictly reduces parse-text worst-case provider work.

## Whole-Plan Consistency Sweep

- Files reread: `plan.md`, all three phase files.
- Decision deltas checked: 11.
- Reconciled stale references: 0 after red-team propagation.
- Unresolved contradictions: 0.
