---
type: research
date: 2026-08-14
status: complete
---

# Parse-Text FatSecret Codepath TDD Research

## Summary

Current `/v1/meals/parse-text` is wired end-to-end, but the FatSecret gate is semantically weak. The live handler already calls FatSecret, but it reads only `food_description`, picks the first result, and silently falls back to AI on timeout or any exception. The adapter already returns structured `*_100g` data from `food.get.v5`, so the bug is not lack of provider data; it is misuse of that data. Public response shape stays stable today, so the safe fix is TDD around the current API plus a narrow refactor seam inside `_cascade_lookup`.

Best path: characterize current behavior first, then replace the weak FatSecret branch with structured candidate selection and validation. Do not touch mobile, DB, image scan, or RAG. Reuse the existing stronger patterns in `IngredientNutritionResolver` and `NutritionLookupService` as reference behavior, but keep parse-text scoped to the current handler and response contract.

## Findings

### 1. Live call chain is simple and fully contained

- Authenticated parse-text route builds `ParseMealTextCommand`, sends it through the event bus, and maps app DTOs to API DTOs in [`src/api/routes/v1/meals_manual_text.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meals_manual_text.py#L141).
- Guest trial uses the same route/handler path after quota reservation in the same file at [`src/api/routes/v1/meals_manual_text.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meals_manual_text.py#L185).
- The event bus registers `ParseMealTextCommand` to `ParseMealTextHandler` in [`src/api/dependencies/event_bus.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/dependencies/event_bus.py#L505).
- The command is only a data carrier: [`src/app/commands/meal/parse_meal_text_command.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/commands/meal/parse_meal_text_command.py#L11).

### 2. Public response shape is stable and should remain unchanged

- API response DTO is `ParseMealTextResponse` with `items`, `total_calories`, `total_protein`, `total_carbs`, `total_fat`, `emoji` in [`src/api/schemas/response/meal_responses.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/schemas/response/meal_responses.py#L68).
- App-layer DTO omits calories and preserves item-level macro fields in [`src/app/schemas/meal_schemas.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/schemas/meal_schemas.py#L10).
- Route mapping recomputes calories from macros via `MacrosModel.total_calories` in [`src/api/routes/v1/meals_route_helpers.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meals_route_helpers.py#L23).
- The approved design explicitly says “return current ParseMealTextResponse shape” and keep the public contract stable in [`plans/reports/260814-1023-parse-text-fatsecret-validation-harness.md`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/plans/reports/260814-1023-parse-text-fatsecret-validation-harness.md#L116).

### 3. Root cause: structured FatSecret data is available but ignored

- `FatSecretService.search_foods()` fetches candidate search results, then enriches each result with `get_food_details()` before returning in [`src/infra/adapters/fat_secret_service.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/fat_secret_service.py#L189).
- `get_food_details()` maps `calories_100g`, `protein_100g`, `carbs_100g`, `fat_100g`, and `allowed_units` from the selected serving in [`src/infra/adapters/fat_secret_service.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/fat_secret_service.py#L269).
- The parse-text helper still parses only `food_description` text in [`src/app/handlers/command_handlers/meal_text_parsing_utils.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/meal_text_parsing_utils.py#L93).
- `_cascade_lookup()` consumes `search_foods()`, takes `fatsecret_results[0]`, calls `parse_fatsecret_nutrition(fs_food)`, and falls back to AI if that parse fails in [`src/app/handlers/command_handlers/parse_meal_text_handler.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/parse_meal_text_handler.py#L268).
- That means the adapter can already hand back structured nutrition, but the handler throws it away and depends on description parsing.

### 4. First-candidate selection is still blind

- `_cascade_lookup()` always selects index zero after `search_foods(..., max_results=5)` in [`src/app/handlers/command_handlers/parse_meal_text_handler.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/parse_meal_text_handler.py#L272).
- The stronger domain pattern already prefers generic candidates and rejects incomplete macro data in [`src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py#L33).
- `NutritionLookupService` also uses a tiered resolution ladder with local reference first, FatSecret second, AI last in [`src/domain/services/meal_suggestion/nutrition_lookup_service.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/nutrition_lookup_service.py#L123).
- Parse-text does not yet reuse that ladder, so candidate quality still depends on provider ordering, not on explicit selection rules.

### 5. Timeout and error swallowing preserve bad AI output

- `_cascade_lookup()` wraps the entire FatSecret branch in `except Exception` and logs only debug, then returns AI macros in [`src/app/handlers/command_handlers/parse_meal_text_handler.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/parse_meal_text_handler.py#L305).
- `search_foods()` itself swallows per-candidate detail failures with `except Exception: pass` and returns the weaker mapped item in [`src/infra/adapters/fat_secret_service.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/fat_secret_service.py#L205).
- The handler also enforces only a divergence cap against AI calories, not a semantic quality gate, in [`src/app/handlers/command_handlers/parse_meal_text_handler.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/parse_meal_text_handler.py#L286).
- Result: a timeout, malformed candidate, or empty description parse can all degrade to AI estimate without any explicit contract-level signal.

### 6. Existing tests cover stability, not the missing semantics

- Handler tests currently cover validation retry, allowed units, provider-outage passthrough, and calorie divergence fallback in [`tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py#L81).
- The “allowed units” test monkeypatches `parse_fatsecret_nutrition()` and `scale_per_100g_nutrition()`, which means it does not exercise the real structured FatSecret path in [`tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py#L124).
- Guest-trial tests confirm the same route surface and auth boundary remain intact in [`tests/unit/api/test_guest_parse_trial.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_guest_parse_trial.py#L99).
- Parse-text route regression exists in [`tests/unit/api/test_routes_with_mocked_event_bus.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_routes_with_mocked_event_bus.py#L329).
- The calorie-parity test confirms the handler’s calorie helper is mathematically consistent, but that does not address semantic truth of inputs in [`tests/unit/domain/test_calorie_formula_parity.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/test_calorie_formula_parity.py#L146).

## Caller / Consumer Inventory

### Live callers

1. Authenticated POST `/v1/meals/parse-text` in [`src/api/routes/v1/meals_manual_text.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meals_manual_text.py#L141).
2. Guest POST `/v1/meals/parse-text/guest-trial` in [`src/api/routes/v1/meals_manual_text.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meals_manual_text.py#L185).
3. Event bus registration for `ParseMealTextCommand` in [`src/api/dependencies/event_bus.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/dependencies/event_bus.py#L505).

### Current consumers

1. API response mapping via [`parsed_food_item_to_response`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/meals_route_helpers.py#L23).
2. Parse-text API schema in [`src/api/schemas/response/meal_responses.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/schemas/response/meal_responses.py#L68).
3. App-layer DTO in [`src/app/schemas/meal_schemas.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/schemas/meal_schemas.py#L10).
4. Regression/characterization tests in:
   - [`tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py#L81)
   - [`tests/unit/api/test_guest_parse_trial.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_guest_parse_trial.py#L99)
   - [`tests/unit/api/test_routes_with_mocked_event_bus.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_routes_with_mocked_event_bus.py#L329)
   - [`tests/unit/domain/test_calorie_formula_parity.py`](/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/domain/test_calorie_formula_parity.py#L146)

## TDD Scenario Matrix

| Phase | Scenario | File / symbol to lock | Expected behavior |
|---|---|---|---|
| Characterize | Auth parse-text happy path | `tests/unit/api/test_routes_with_mocked_event_bus.py::test_meals_parse_text_happy_path` | Response shape unchanged |
| Characterize | Guest parse-text happy path | `tests/unit/api/test_guest_parse_trial.py::test_guest_parse_success` | Same public shape, no auth dependency |
| Characterize | AI validation retry | `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py::test_parse_text_retries_invalid_ai_output_once` | One retry only |
| Characterize | Provider outage stays non-fatal | `tests/unit/handlers/command_handlers/test_parse_meal_text_handler.py::test_parse_text_does_not_retry_provider_outage` | No extra retry on provider outage |
| Characterize | Calorie parity | `tests/unit/domain/test_calorie_formula_parity.py::test_parse_meal_text_handler` | Derivation helper remains stable |
| Add failing test | Structured FatSecret details accepted | new handler test around `_cascade_lookup()` | Use `*_100g`, not `food_description` |
| Add failing test | Wrong first candidate rejected | new handler test around candidate selection | Do not blindly take index 0 |
| Add failing test | Timeout does not silently fake FatSecret confidence | new handler test around `_cascade_lookup()` | Keep `data_source` honest |
| Add failing test | Incomplete structured macros rejected | new FatSecret adapter/handler test | No confident FatSecret result without required fields |
| Add failing test | `100gr khoai tây` no 890 kcal regression | new golden test | Valid potato result, not implausible AI macro output |
| Refactor seam | Pure FatSecret selection/validation helper | `parse_meal_text_handler.py` private helper or new module | Isolate candidate choice and structured validation |
| Refactor seam | Reuse shared structured lookup pattern | optional adapter to `ingredient_nutrition_resolver.py` shape | Avoid a third nutrition lookup design |

## Recommendation

Ranked:

1. Add characterization tests first, then a narrow structured FatSecret helper inside `ParseMealTextHandler`. Highest fit, lowest blast radius, keeps public contract stable.
2. Reuse the same candidate selection rules already proven in `IngredientNutritionResolver` and `NutritionLookupService`. Good architectural fit, but do it as a local parse-text seam first, not a cross-cutting rewrite.
3. Add a separate harness only after the core behavior is locked. Useful for regression tracking, but not the first fix.

Why this ranking:

- Best source credibility is the live code path itself plus existing stronger domain patterns. The brainstorm report is consistent with the code, but it is still a design artifact, not proof.
- Trade-off is clear: structured validation costs a bit more code, but removes the blind first-result / description-parse failure mode.
- Adoption risk is low if the refactor stays inside parse-text and preserves response DTOs. Risk rises if this is generalized into a new shared nutrition framework too early.
- Architectural fit is strong because the repo already has a structured, tiered nutrition pattern; parse-text is just lagging behind that standard.

## Minimum Safe Refactor Seams

1. Extract a pure function that scores/filters FatSecret candidates from search results.
2. Extract a pure function that validates structured `*_100g` fields and metric serving before scaling.
3. Keep `_cascade_lookup()` as the orchestration shell only.
4. Keep route mapping and response DTOs untouched.
5. Preserve AI fallback as controlled fallback, not as a silent default on provider ambiguity.

## Limitations

- I did not run the parse-text suite or live provider calls; this is read-only codepath research.
- I did not inspect production FatSecret payloads, so candidate-ranking edge cases are inferred from adapter shape, not from live vendor examples.
- I did not design the final harness implementation; this report only specifies the safe TDD surface and refactor boundaries.

## Next Step

Create the implementation plan from this report, then add characterization tests before touching `_cascade_lookup()` or the FatSecret adapter.
