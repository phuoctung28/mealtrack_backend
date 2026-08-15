---
type: brainstorm
date: 2026-08-14
status: approved
---

# Brainstorm: Parse-Text FatSecret Validation Harness

## Summary

Improve `/v1/meals/parse-text` without changing its public response contract. AI
parses food identity, preparation, and quantity; local `food_reference` and
FatSecret own verified macros; backend derives calories; an offline/live
evaluation harness prevents semantic regressions. Full vector RAG is excluded.

## Problem And Requirements

Observed failure: `100gr khoai tây` produced about 890 kcal. The current system
can derive 890 kcal correctly from implausible AI macros, so arithmetic safety
does not provide nutrition accuracy.

Approved requirements:

- Scope only authenticated and guest `/parse-text` flows sharing
  `ParseMealTextHandler`.
- Keep current API and mobile contracts backward compatible.
- Improve prompt extraction and FatSecret verification together.
- Use structured FatSecret per-100g fields, not human-readable description
  parsing, whenever structured fields exist.
- Prefer verified reference nutrition over AI macros after a confident match.
- Add a repeatable parse-text nutrition evaluation harness.
- Do not add a vector database or full RAG pipeline.

Out of scope:

- Meal image analysis and food-label scanning.
- Mobile UI changes or new response states.
- Provider migration, database redesign, or a new nutrition vendor.
- Using embeddings to retrieve or calculate exact nutrition values.

## Findings

### Arithmetic Is Correct But Inputs Are Not Trusted

`MealTextNutritionResponse` validates output shape and broad numeric bounds.
`ParseMealTextHandler` derives calories from AI macros, then applies a generic
physical ceiling of 9 kcal per gram. A 100 g item at 890 kcal remains below that
ceiling and survives despite being absurd for potato.

Evidence:

- `src/domain/model/ai/nutrition_contracts.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `src/domain/services/nutrition_calculation_service.py`
- `src/domain/model/nutrition/macros.py`

An isolated reproduction confirmed the existing vision nutrition contract also
accepts a 100 g food with 98.8889 g fat and derives exactly 890 kcal. This proves
schema validity and calorie derivation are insufficient semantic checks.

### FatSecret Verification Exists But Has A Weak Boundary

`ParseMealTextHandler._cascade_lookup()` searches FatSecret but selects the first
result without deterministic identity or preparation scoring. It then parses
`food_description`, although `FatSecretService.search_foods()` already enriches
results with structured `calories_100g`, `protein_100g`, `carbs_100g`, and
`fat_100g`. Lookup, mapping, and timeout errors are swallowed and silently fall
back to AI estimates.

Relevant code:

- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `src/app/handlers/command_handlers/meal_text_parsing_utils.py`
- `src/infra/adapters/fat_secret_service.py`

### A Better Lookup Pattern Already Exists

`IngredientNutritionResolver` consumes structured FatSecret per-100g values,
prefers generic candidates, and warms `food_reference`. `NutritionLookupService`
already implements local reference to FatSecret to AI fallback with backend
scaling and derived calories. Parse-text should reuse or share this behavior
instead of maintaining a weaker parallel lookup.

Relevant code:

- `src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py`
- `src/domain/services/meal_suggestion/nutrition_lookup_service.py`
- `src/infra/repositories/food_reference_repository_async.py`

### Current Prompt Harness Does Not Measure Nutrition Accuracy

`PromptEvalLoop` measures vision schema parsing, validation success, and prompt
size. It does not execute the parse-text pipeline or measure canonical identity,
quantity conversion, FatSecret candidate selection, reference coverage, calorie
error, catastrophic outliers, latency, or provider-call count.

Relevant code:

- `src/domain/services/meal_analysis/prompt_eval_loop.py`
- `scripts/development/evaluate_meal_analyze_prompt_candidates.py`
- `tests/unit/domain/services/meal_analysis/test_prompt_eval_loop.py`

## Evaluated Approaches

| Approach | Advantages | Disadvantages | Decision |
|---|---|---|---|
| Prompt-only nutrition estimates | Small change, no provider work | Cannot guarantee semantic correctness; model still invents macros | Reject |
| Better prompt plus deterministic FatSecret verification | Structured truth, explainable scaling, reuses current services | Requires candidate matching and fallback policy | Approve |
| Full vector RAG over nutrition documents | Flexible natural-language retrieval | Stale data, unit ambiguity, opaque ranking, unnecessary infrastructure | Reject |
| Constrained AI candidate adjudication | Can help ambiguous preparation/name cases | Adds cost and another probabilistic decision | Defer; optional tie-breaker only |

## Approved Design

### Target Flow

```text
user text
  -> AI structured extraction
       display name
       canonical English lookup name
       preparation state
       quantity and unit
       quantity_g
       provisional macros
  -> local food_reference exact normalized lookup
  -> FatSecret candidate search on miss
  -> deterministic candidate scoring
  -> fetch one selected candidate's structured details
  -> validate per-100g nutrition
  -> scale by quantity_g / 100
  -> derive calories from scaled macros
  -> return current ParseMealTextResponse shape
```

### Prompt And Contract

Enhance the internal parse-text contract to require or normalize:

- Canonical English food identity for database/provider lookup.
- Preparation state such as raw, boiled, baked, fried, mashed, or unknown.
- `quantity_g` when input contains a weight or can be converted confidently.
- Provisional macro estimates only as a bounded fallback.

For non-English input, keep the localized display name while separating lookup
identity from presentation. Do not infer a preparation that the user did not
provide; use `unknown` and prefer a generic FatSecret result.

### Candidate Selection

Do not accept result index zero automatically. Rank candidates using:

1. Exact normalized canonical-name match.
2. Preparation-state match.
3. Generic food preference when no brand was supplied.
4. Complete metric serving and structured macro availability.
5. Avoid branded, concentrate, dry mix, supplement, or prepared variants unless
   the user text supports that form.

Use candidate search followed by one selected detail request. Avoid fetching
full details for all five candidates when one can be selected deterministically.

### Structured Nutrition Verification

Use `protein_100g`, `carbs_100g`, `fat_100g`, optional fiber/sugar, and metric
serving fields from the FatSecret adapter. Keep description regex parsing only
as a legacy fallback.

Accept a reference only when:

- Required macro fields are numeric and non-negative.
- Metric serving amount is positive and supports per-100g normalization.
- Total macro mass is physically plausible with a small source-rounding margin.
- Declared provider energy is reasonably consistent with backend-derived energy.
- Candidate identity/preparation score clears the confidence threshold.

After acceptance, reference macros replace AI macros. Backend calorie derivation
remains authoritative.

### Fallback

If local and FatSecret resolution fail:

1. Retry AI once with compact validation feedback and the required canonical
   identity/quantity contract.
2. Apply quantity-aware physical checks to the retry.
3. Return the existing AI-estimate response only when it passes the fallback
   checks; otherwise raise the existing controlled validation failure.

Do not let provider failure, incomplete fields, or an implausible result silently
become a confident FatSecret response. Preserve `data_source` accurately.

### Evaluation Harness

Add a parse-text-specific harness with versioned, non-PII golden cases covering:

- Vietnamese and English common foods.
- Exact gram input, countable servings, and ambiguous units.
- Preparation variants with materially different energy density.
- Oils, sauces, drinks, raw ingredients, cooked staples, and compound dishes.
- Provider miss, timeout, incomplete structured data, and wrong first candidate.
- Catastrophic regression case: `100gr khoai tây` must never return about 890 kcal.

Run two modes:

- Deterministic CI mode with recorded/synthetic FatSecret fixtures and no network.
- Explicit development/staging live mode using configured providers, never CI
  secrets or production user data.

Measure:

| Metric | Initial gate |
|---|---:|
| Public response contract pass rate | 100% |
| Catastrophic nutrition outliers in golden common foods | 0 |
| Canonical identity and quantity extraction | at least 95% |
| Correct candidate selection in covered cases | at least 95% |
| Common-food reference resolution | at least 90% |
| FatSecret result with missing/invalid structured macros accepted | 0 |
| Provider calls per resolved item | bounded and reported |
| p50/p95 latency | reported before rollout |

Thresholds are starting quality gates and may tighten after the first measured
baseline. Do not lower them merely to make CI pass.

## Implementation Touchpoints

Likely modifications:

- `src/domain/services/prompts/system_prompts.py`
- `src/domain/model/ai/nutrition_contracts.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `src/domain/services/meal_suggestion/ingredient_nutrition_resolver.py`
- `src/domain/services/meal_suggestion/nutrition_lookup_service.py`
- `src/api/dependencies/event_bus.py`
- Focused unit tests for parse-text, resolver, lookup, and response compatibility.

Likely new harness artifacts belong under `scripts/development/` and
`tests/fixtures/`; exact names and ownership belong in the implementation plan.

No expected changes:

- `/v1/meals/parse-text` response schema.
- Flutter/mobile code.
- Database schema.
- Meal image or food-label analysis.

## Risks And Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Wrong FatSecret candidate | Correct-looking but wrong nutrition | Deterministic identity/preparation score; never blind first-result selection |
| Higher request latency | Slower parse-text UX | Local reference first; one candidate detail call; bounded timeout; warm existing reference store |
| FatSecret outage | More AI fallbacks | Accurate source tagging, one bounded retry, semantic validation, operational metrics |
| Overly strict rejection | Valid uncommon foods fail | Separate reference confidence from physical validity; retain bounded AI fallback |
| Golden dataset overfits | Harness passes while production drifts | Diverse multilingual cases plus explicit live staging evaluation |
| Vector RAG scope creep | More infrastructure without exactness | Keep structured lookup; defer embeddings unless a distinct retrieval problem is proven |

## Success Criteria

- `100gr khoai tây` resolves a generic potato identity and valid 100 g reference
  nutrition; AI macros cannot override a confident reference.
- Structured FatSecret per-100g fields drive scaling; description parsing is only
  a compatibility fallback.
- Wrong or incomplete candidates do not claim `data_source="fatsecret"`.
- AI fallback cannot return the reproduced 890 kcal potato result.
- Existing authenticated and guest parse-text response contracts remain stable.
- Deterministic harness passes all gates; live evaluation reports accuracy,
  fallback, latency, and provider-call metrics separately.

## Recommendations

1. Create a TDD implementation plan from this approved report.
2. Characterize current parse-text and FatSecret behavior with golden regression
   tests before changing the prompt or resolver.
3. Reuse the structured resolver/lookup ladder instead of adding a third lookup
   implementation.
4. Add the semantic harness gate before comparing prompt variants.
5. Roll out with source-tier and fallback metrics; do not add vector RAG.

## Unresolved Questions

None.
