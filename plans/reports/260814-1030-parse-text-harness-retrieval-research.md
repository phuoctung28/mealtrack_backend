# Parse-Text Harness Retrieval Research

Date: 2026-08-14

## Summary

The right move is a small deterministic CI harness around `/v1/meals/parse-text`, plus an explicit live staging mode for provider evals. Do not build full vector RAG. The current stack already has the correct structural pieces: AI parses text, `food_reference` provides exact normalized lookup, FatSecret provides structured per-100g nutrition, and backend calorie math stays authoritative. The gap is semantic quality, not arithmetic.

The approved design already states the failure mode: `100gr khoai tây` can still become ~890 kcal if the AI emits implausible macros, because valid schema + correct math is not semantic truth. The harness should therefore score extraction, candidate selection, reference acceptance, fallback behavior, and latency/call-count, not just prompt parse success. See the approved design at [plans/reports/260814-1023-parse-text-fatsecret-validation-harness.md#L11](./260814-1023-parse-text-fatsecret-validation-harness.md#L11).

## Evidence

- `ParseMealTextHandler` already does structured-output validation, one retry on invalid AI output, then a FatSecret fallback with a 3s timeout, then AI fallback. It also still parses `food_description` as the fallback path. See [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/parse_meal_text_handler.py#L63](./src/app/handlers/command_handlers/parse_meal_text_handler.py#L63) and [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/app/handlers/command_handlers/parse_meal_text_handler.py#L242](./src/app/handlers/command_handlers/parse_meal_text_handler.py#L242).
- `NutritionLookupService` already implements the better pattern: Redis -> exact normalized `food_reference` -> FatSecret resolver -> AI fallback, with batched T1 lookups and derived calories. See [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/nutrition_lookup_service.py#L123](./src/domain/services/meal_suggestion/nutrition_lookup_service.py#L123).
- `IngredientNutritionResolver` already prefers `Generic` results, requires structured `protein_100g` / `carbs_100g` / `fat_100g`, and warms `food_reference`. See [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py#L33](./src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py#L33).
- `FatSecretService` already exposes the structured candidate/detail boundary and per-100g normalization from `metric_serving_amount`; description parsing is legacy only. See [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/fat_secret_service.py#L233](./src/infra/adapters/fat_secret_service.py#L233) and [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/fat_secret_service.py#L345](./src/infra/adapters/fat_secret_service.py#L345).
- Existing prompt eval code only measures parser validity and prompt size. It does not measure nutrition correctness, latency, or provider calls. See [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/meal_analysis/prompt_eval_loop.py#L26](./src/domain/services/meal_analysis/prompt_eval_loop.py#L26) and [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/scripts/development/evaluate_meal_analyze_prompt_candidates.py#L20](./scripts/development/evaluate_meal_analyze_prompt_candidates.py#L20).
- Observability already supports safe low-cardinality attributes such as `ai_purpose`, `source`, `language`, `status`, `cache_hit`, and `ai_model`, which is enough for eval metrics without leaking prompts or candidate text. See [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/observability_connectors.py#L8](./src/observability_connectors.py#L8) and [/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/monitoring/test_observability_facade.py#L63](./tests/unit/infra/monitoring/test_observability_facade.py#L63).

## Recommendation

Ranked:

1. Deterministic CI harness with frozen goldens, synthetic FatSecret fixtures, and zero network.
2. Optional live staging eval mode behind an explicit flag and non-production credentials.
3. Constrained AI candidate adjudication only if deterministic scoring still fails on a small, observed ambiguity set.
4. Full vector RAG: reject for this scope.

Why:

- The current retrieval problem is not open-ended semantic search. It is exact identity + preparation + quantity resolution followed by one verified nutrition source. That fits structured retrieval, not vector RAG.
- FatSecret already provides structured candidate search and per-100g detail fields. Adding embeddings would add stale ranking risk, opaque failure modes, and extra infra without improving exact nutrition truth.
- The approved design explicitly excludes a vector database and says candidate adjudication should be deferred unless a distinct retrieval problem is proven. See [plans/reports/260814-1023-parse-text-fatsecret-validation-harness.md#L105](./plans/reports/260814-1023-parse-text-fatsecret-validation-harness.md#L105).

## Proposed Harness

### CI Mode

- Use versioned, non-PII golden cases.
- Mock FatSecret with recorded/synthetic fixtures only.
- Keep the test deterministic and hermetic.
- Gate on public response contract, catastrophic outliers, extraction accuracy, candidate selection, and reference acceptance.

### Live Staging Mode

- Explicit opt-in only.
- Use real configured providers in dev/staging.
- Record only aggregate metrics and counts.
- Never run in CI, never use production user data, never store raw prompts or full candidate payloads.

### Golden Corpus

- Vietnamese and English common foods.
- Exact gram inputs, countable servings, and ambiguous units.
- Raw, boiled, baked, fried, mashed, and unknown preparation states.
- Oils, sauces, drinks, raw ingredients, cooked staples, compound dishes.
- Provider miss, timeout, incomplete structured data, and wrong-first-candidate cases.
- Regression sentinel: `100gr khoai tây` must never return ~890 kcal.

## Metrics And Gates

| Metric | Gate |
|---|---:|
| Public response contract pass rate | 100% |
| Catastrophic outliers | 0 |
| Canonical identity + quantity extraction | >= 95% |
| Correct candidate selection | >= 95% |
| Common-food reference resolution | >= 90% |
| Invalid structured FatSecret accepted | 0 |
| Provider calls per resolved item | bounded and reported |
| p50 / p95 latency | reported before rollout |

Use `distribution_metric` for latency and `increment_metric` for counts, with low-cardinality attributes only. Suggested names:

- `parse_text.eval.latency_ms`
- `parse_text.eval.provider_calls`
- `parse_text.eval.reference_hit`
- `parse_text.eval.semantic_outlier`
- `parse_text.eval.fallback_used`

## Performance And Privacy Risks

- Highest latency risk is candidate search plus detail fetch. Keep it to one selected candidate detail call, not full fetch-for-all.
- Extra AI adjudication adds latency and cost, and it creates a second probabilistic decision surface.
- Live evals must not emit raw prompts, food names, full payloads, or candidate dumps into logs or metrics.
- Keep all eval dimensions aggregate and low-cardinality; the existing observability allowlist is already compatible with that.

## Why Full RAG Is Not Needed

RAG helps when the task is broad semantic retrieval over fuzzy documents. This task is narrower: map text to a food identity, check a local exact match, then verify one structured provider record. The repo already has:

- exact normalized local lookup,
- generic-vs-branded candidate preference,
- structured per-100g FatSecret detail extraction,
- backend calorie derivation,
- and a bounded AI fallback.

That is enough to solve the current failure mode. Vector RAG would be extra machinery with more ways to drift, not a better truth source.

## Unresolved Questions

- What exact tolerance should qualify a FatSecret candidate as a confident match for preparation state?
- Should live staging evals write to a separate report artifact or only to metrics plus console output?
- Do we want one shared gold corpus for CI/live, or a smaller live-only stress slice?
