---
type: brainstorm-report
date: 2026-06-13
status: approved-for-planning
topic: llm-nutrition-output-contracts
---

# LLM Nutrition Output Contract Brainstorm

## Summary

MealTrack should treat Gemini as a probabilistic extractor, not a trusted
nutrition engine. The proper fix is contract-first LLM orchestration:
structured output, deterministic validation, one bounded retry, then domain
mapping. Parser cleanup is only a last safety guard.

Recommended next step: `/ck:plan --tdd` because this changes critical nutrition
behavior, AI provider contracts, and retry semantics.

## Problem

Production failure:

- Gemini returned `quantity=150000`.
- Parser accepted the payload until `FoodItem` domain validation rejected it.
- Previous local patch filtered impossible food items after model output.
- That prevents a crash, but it can silently save incomplete or misleading
nutrition.

Root issue: the LLM boundary lacks a strong output contract and semantic
validation loop.

## Requirements

Expected output:

- A design for robust image/text/recipe AI nutrition output handling.
- Implementation plan later, not in this brainstorm.

Acceptance criteria:

- `quantity=150000` never creates a saved food item.
- Invalid model output triggers one automatic retry.
- Retry success returns normal meal UX.
- Retry failure returns controlled user-facing guidance.
- No raw parser/domain exception leaks to API clients.
- Calories remain backend-derived from macros.
- Image, text, and recipe AI flows use explicit contracts.

Scope:

- In scope: vision scan, text parse, recipe output contracts, AI provider
  schema support, validation retry, parser/domain boundary.
- Out of scope now: DB schema changes, mobile UI changes, nutrition database
  redesign, broad model-provider migration.

Non-negotiable constraints:

- Preserve user experience over strict fail-fast behavior.
- Follow Clean Architecture and CQRS boundaries.
- Keep domain invariants as final guard.
- Do not trust AI-reported calories as source of truth.
- Prefer simple bounded retries over multi-pass agent repair.

Touchpoints:

- `src/infra/services/ai/providers/gemini_provider.py`
- `src/infra/services/ai/ai_model_manager.py`
- `src/infra/adapters/vision_ai_service.py`
- `src/domain/parsers/gpt_response_parser.py`
- `src/domain/parsers/vision_response_models.py`
- `src/domain/model/ai/gpt_response.py`
- `src/infra/services/ai/schemas.py`
- upload/scan-by-url/background meal analysis handlers
- parser/provider/handler tests

## Findings

- Text generation already supports `schema` via `with_structured_output`.
- Vision generation currently sends multimodal prompt input but parses raw JSON
  text afterward.
- Existing recipe work is closer to the right architecture: AI proposes recipe
  ingredients; deterministic code computes nutrition.
- The codebase has duplicate AI response schema concepts. This creates drift.
- Prompt-only instructions like "realistic quantity" are insufficient.

References:

- Gemini structured outputs:
  https://ai.google.dev/gemini-api/docs/structured-output
- LangChain Gemini multimodal input:
  https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai
- LangChain structured output:
  https://reference.langchain.com/python/langchain-google-genai/chat_models/ChatGoogleGenerativeAI/with_structured_output

## Evaluated Approaches

### Option A: Keep parser filtering

Pros:

- Smallest patch.
- Prevents immediate crash.
- Low implementation risk.

Cons:

- Silently hides model failure.
- Can save incomplete meal nutrition.
- Does not improve LLM reliability.
- Hard to observe invalid-output rates.

Verdict: temporary seatbelt only, not final design.

### Option B: Clamp invalid values

Pros:

- Simple.
- Avoids exceptions.

Cons:

- Invents food quantities.
- Corrupts macros and calories.
- Worse than dropping because it manufactures confidence.

Verdict: reject.

### Option C: Contract-first LLM boundary with bounded retry

Pros:

- Fits well-designed LLM architecture.
- Makes invalid output visible and retryable.
- Preserves UX through automatic retry.
- Keeps domain model clean and deterministic.
- Scales across image, text, and recipe flows.

Cons:

- More files touched.
- Requires provider contract changes.
- Needs tests for both schema and semantic validation.
- Need spike/verification for structured multimodal output path.

Verdict: recommended.

## Final Recommendation

Implement Option C.

Pipeline:

```text
prompt + media/context
  -> structured model call
  -> Pydantic contract validation
  -> semantic nutrition validation
  -> one bounded retry on invalid AI output
  -> deterministic domain mapping
  -> domain invariant
```

Design decisions:

- Add `schema` support to `generate_with_vision`.
- Use Gemini/LangChain structured output for multimodal meal scan responses.
- Consolidate duplicated response models into one AI schema module.
- Use task-specific contracts:
  - `VisionNutritionResponse`
  - `MealTextNutritionResponse`
  - `RecipeDetailsResponse`
- Prefer grams for AI nutrition output: `quantity_g`.
- Let domain mapping convert `quantity_g` to `FoodItem(quantity=..., unit="g")`.
- AI may provide macros. Backend derives calories from macros.
- AI-reported `calories` should be removed or treated as ignored metadata.
- `quantity=150000` is invalid AI output, not a food item.
- Retry once with correction context. No unbounded repair loop.
- If retry fails, return user-safe guidance to retake photo or add context.
- Parser remains defensive but must not silently turn invalid model output into
  trusted nutrition.

## Implementation Considerations

- Provider layer should return already-validated dicts or Pydantic dumps.
- Validation errors should include field path, model name, strategy, and attempt.
- Logs must avoid raw image content and large user food payloads.
- Existing fast-path retry should distinguish provider outage from invalid AI
  output.
- Backward compatibility may need a temporary raw-JSON fallback while tests prove
  multimodal structured output works reliably.
- Prompt eval loop should be expanded beyond parse success.

## Risks

| Risk | Mitigation |
|------|------------|
| LangChain structured vision path behaves differently from text path | Start with provider-level spike/test |
| Schema too strict causes UX failures | One retry, friendly fallback, observe invalid-output rate |
| Schema too loose repeats same bug | Semantic validation after schema validation |
| More latency from retry | Retry only invalid structured output, not every low-confidence scan |
| Duplicate contracts drift again | One canonical AI schema module |

## Validation Criteria

Tests should cover:

- `generate_with_vision(..., schema=VisionNutritionResponse)` passes schema to
  provider.
- Gemini provider uses structured output for multimodal messages.
- Invalid quantity raises validation before domain mapping.
- Invalid AI output triggers one retry.
- Retry success saves meal normally.
- Retry failure returns controlled application error.
- Parser no longer silently drops impossible over-limit food items as final
  behavior.
- Text parsing and recipe generation follow explicit contracts.
- Calories derive from macros in backend.

Operational validation:

- Track invalid output rate by model, strategy, prompt version.
- Track retry recovery rate.
- Alert if invalid output spikes after prompt/model changes.

## Next Steps

1. Create `/ck:plan --tdd` from this report.
2. First phase should be a provider-level structured multimodal output spike.
3. Then consolidate contracts and write failing tests around `150000`.
4. Replace parser workaround with contract validation and retry behavior.
5. Update docs/roadmap after implementation.

## Unresolved Questions

None.
