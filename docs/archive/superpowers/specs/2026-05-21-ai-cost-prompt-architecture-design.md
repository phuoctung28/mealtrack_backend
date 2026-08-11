# AI Cost & Prompt Architecture Design
**Date:** 2026-05-21
**Status:** Draft — awaiting review
**Scope:** Gemini cost reduction + prompt architecture redesign for 1M users

---

## TL;DR

Six bugs are silently inflating costs today. Two structural problems will make those
costs catastrophic at scale. This spec fixes all of them in four rollout phases.

At 40 users the bill is ~$12/month. At 1M users with the current architecture it
would reach ~$300k/month. With all changes applied: ~$30–40k/month.

---

## 1. Background

MealTrack uses Gemini 2.5 Flash as its primary AI model via LangChain for:
- **Meal image scanning** — photo → nutrition JSON (vision)
- **Recipe generation** — 3 parallel calls per user tap
- **Meal discovery** — 1 call for 10 meal names + macros
- **Text / barcode parsing** — text → structured nutrition

The AI layer has two providers today (Gemini + Mistral) with a fallback chain,
a circuit breaker, and a purpose-based model routing system.

---

## 2. Current State Problems

### 2.1 Bugs inflating costs right now

**Bug 1 — Thinking tokens not actually disabled for recipes (silent)**

`gemini_model_config.py` sets `thinking_budget=0` for `RECIPE_PRIMARY` and
`RECIPE_SECONDARY`. But `gemini_provider.py:16` maps every model string to
`GeminiModelPurpose` using `MODEL_PURPOSE_MAP`, which only contains:

```python
MODEL_PURPOSE_MAP = {
    "gemini-2.5-flash":      GeminiModelPurpose.GENERAL,
    "gemini-2.5-flash-lite": GeminiModelPurpose.MEAL_NAMES,
}
```

Recipe calls arrive as `model="gemini-2.5-flash"` → resolved to `GENERAL` →
`thinking_budget=0` branch is never reached. **Thinking is enabled on every
recipe call.** At ~2,000–4,000 hidden thinking tokens per call at output token
rates, this doubles the recipe cost silently.

**Bug 2 — Recipe output limit 4,000 is 4× too high**

`recipe_attempt_builder.py:30`: `PARALLEL_SINGLE_MEAL_TOKENS = 4000`

A complete recipe (8 ingredients + 5 steps) is ~400–600 tokens of actual
content. The 4,000 limit tells Gemini it may generate 10× that — holding the
connection open and over-billing on output tokens.

**Bug 3 — Vision output limit 4,096 is 8× too high**

`gemini_provider.py:104`: `max_output_tokens=kwargs.get("max_tokens", 4096)`

A meal scan JSON response is ~300–500 tokens. The 4,096 limit creates the same
over-billing pattern.

**Bug 4 — Temperature 0.7 everywhere**

`GeminiModelManager._create_model()` hardcodes `temperature=0.7` for all
purposes. Best practice: structured JSON extraction → 0.1, generation → 0.4.
Using 0.7 for barcode/text parsing increases hallucination and JSON parse
failures, which trigger retries, which cost more.

**Bug 5 — Four vision strategies never modernised**

`BasicAnalysisStrategy` was optimised to a compact format. The other four
(`PortionAware`, `IngredientAware`, `WeightAware`, `UserContextAware`) still use
the old verbose multi-line indented format and append the full 400-char
`SCAN_DECOMPOSITION_RULES`. They were missed when `BasicAnalysisStrategy` was
updated.

**Bug 6 — Same rules defined 3–4 times across different files**

| Rule | Defined in |
|---|---|
| Decomposition | `prompt_constants.py`, `meal_analysis_strategy.py` (×2 variants), `system_prompts.py` inline |
| Emoji | `prompt_constants.py`, `meal_analysis_strategy.py`, `system_prompts.py` |
| Macro accuracy | `prompt_constants.py`, various prompts inline |
| Recipe system | Hardcoded inline in `parallel_recipe_generator.py` in 3 separate methods |

Every call re-sends duplicate rule text. Every fix must be applied in 4 places.

### 2.2 Structural problems that matter at 1M users

**Problem 1 — No prompt caching**

System messages are ~80 tokens. Gemini implicit caching requires ≥1024 tokens.
Explicit caching requires the static content to be separated from dynamic
variables. Currently rules, schema, and user variables are all mixed into the
user message. Every call pays full price for the static portion.

**Problem 2 — No operational infrastructure for scale**

| Missing | Impact at 1M users |
|---|---|
| Single Gemini API key | 2,000 RPM cap. 1M users × 1% active × 3 calls = 30,000 RPM needed |
| No per-user token budget | One bot integration can generate millions of calls |
| No prompt versioning | Can't safely deploy prompt changes without risking 1M users |
| No LLM observability | No visibility into cost per feature, per user, or per model |
| No request backpressure | Peak load holds thousands of open HTTP connections |

---

## 3. Goals

- Reduce per-call token cost by ≥70% vs current (across all features)
- Fix the recipe 503 spike amplification (separate from cost — see debug notes)
- Make all prompt rules a single source of truth
- Instrument every AI call with tokens, cost, latency via PostHog LLM Analytics
- Design infrastructure to handle 1M users without architectural rework
- Keep rollout safe: changes deployed in phases, quick wins first

## 4. Non-Goals

- Switching AI providers (Gemini stays primary)
- Replacing LangChain
- Rebuilding the CQRS/event bus layer
- Per-user personalised prompts (deferred)
- Streaming recipe responses (deferred)

---

## 5. Architecture Design

### 5.1 Prompt Split: Static System / Dynamic User

**Principle:** everything that does not change between users or calls belongs in
the system message. Everything that does change belongs in the user message.

**Target structure for recipe generation:**

```
System message (~1,100 tokens, static, cached):
  - Role definition
  - Complete JSON schema with 2 worked examples (few-shot)
  - Decomposition rules with examples
  - Ingredient rules (amounts, units, conversions)
  - Emoji selection rules
  - Language rules (English-only)
  - Scaling / serving rules
  - Output validation instructions

User message (~80 tokens, dynamic):
  Meal: "Grilled Chicken Salad"
  Target: 450 cal | 1 serving | ≤30 min
  Ingredients: chicken breast, lettuce, cherry tomatoes
  Allergies: none
```

**Why ≥1,024 tokens for system message:** this is Gemini 2.5 Flash's minimum
for context caching eligibility. The extra tokens come from adding 2 full
worked examples (few-shot). Few-shot examples also reduce parse failures — dual
benefit.

**Same pattern applied to:**
- Vision system message (all 5 strategies share one static system prompt)
- Discovery system message
- Text/barcode parse system message

### 5.2 Explicit Context Caching

At 1M users, Gemini's implicit caching has no guaranteed hit rate under heavy
concurrent load. Explicit caching creates a stable cache ID controlled by the
application — every call references it, 90% off guaranteed.

**Implementation: `GeminiCacheManager`** (new file)

```python
# src/infra/services/ai/gemini_cache_manager.py

class GeminiCacheManager:
    """Creates and refreshes Gemini explicit context caches. Singleton."""

    CACHE_TYPES = {
        "recipe":     (RECIPE_SYSTEM_PROMPT,     "gemini-2.5-flash"),
        "vision":     (VISION_SYSTEM_PROMPT,     "gemini-2.5-flash"),
        "discovery":  (DISCOVERY_SYSTEM_PROMPT,  "gemini-2.5-flash-lite"),
        "text_parse": (TEXT_PARSE_SYSTEM_PROMPT, "gemini-2.5-flash-lite"),
    }
    TTL_SECONDS = 3600
    REFRESH_BEFORE_EXPIRY = 600  # refresh at 50 min, not 60

    def get_cache_name(self, cache_type: str) -> str | None:
        """Return cache name from Redis, or None if not yet created."""

    async def warm_all(self) -> None:
        """Create all caches at startup. Called from app lifespan."""

    async def refresh_loop(self) -> None:
        """Background task: refresh caches every REFRESH_BEFORE_EXPIRY seconds."""
```

**Cache lifecycle:**
1. App startup: `warm_all()` creates 4 caches, stores names in Redis
   (`gemini_cache:recipe`, `gemini_cache:vision`, etc.)
2. Background task refreshes every 50 minutes before the 1-hour TTL expires
3. `GeminiProvider.generate()` reads cache name from Redis, passes as
   `cached_content` to `ChatGoogleGenerativeAI`
4. If cache name is missing (Redis miss or creation failed): falls back to
   uncached call — no error, just no discount

**Cost impact of explicit caching at 1M users:**

| | Without caching | With explicit caching |
|---|---|---|
| Input tokens per recipe call | ~1,100 (system + user) | 80 normal + 1,020 cached |
| Effective rate (cached portion) | $0.30/1M | $0.03/1M |
| At 3M recipe calls/day | ~$990/day input | ~$55/day input |
| Monthly input savings | — | **~$28,000/month** |

### 5.3 Rule Consolidation

Single source of truth: `prompt_constants.py`.

**Delete from codebase:**
- `SCAN_DECOMPOSITION_RULES` in `meal_analysis_strategy.py`
- `BASIC_SCAN_DECOMPOSITION_RULES` in `meal_analysis_strategy.py`
- Inline recipe system strings in `parallel_recipe_generator.py` (3 copies)

**Update:**
- `SystemPrompts` class imports constants from `prompt_constants.py`
- `ParallelRecipeGenerator` uses `SystemPrompts.RECIPE_GENERATION` constant
- All 5 vision strategies reference `SystemPrompts.VISION_ANALYSIS`

**Result:** changing a rule requires editing one line in one file.

### 5.4 Vision Strategy Modernisation

All 5 strategies share a single static system message (`SystemPrompts.VISION_ANALYSIS`,
≥1,024 tokens). Strategy-specific context moves to the user message only.

```python
# Before (PortionAwareAnalysisStrategy.get_user_message):
# 15 lines of verbose prose

# After:
def get_user_message(self) -> str:
    return (
        f"Analyze this food image.\n"
        f"Portion context: {self.portion_size} {self.unit}. "
        f"Scale all nutrition values to match this portion."
    )
```

Since all vision calls share one system prompt → one cache entry → every vision
call from every user hits the same cache. No additional cache entries needed.

### 5.5 Temperature Calibration

`GeminiModelManager.get_model_for_purpose()` applies purpose-specific temperature:

```python
PURPOSE_TEMPERATURES = {
    GeminiModelPurpose.GENERAL:        0.2,
    GeminiModelPurpose.MEAL_NAMES:     0.7,  # keep — diversity is the point
    GeminiModelPurpose.RECIPE:         0.4,
    GeminiModelPurpose.BARCODE:        0.1,
}
```

Vision calls (`generate_with_vision`) use `temperature=0.2` — accuracy matters
more than creativity for food identification.

### 5.6 Output Token Limits

| Location | Current | Target | Worst-case actual output | Safety margin |
|---|---|---|---|---|
| `recipe_attempt_builder.py:30` | 4,000 | **1,200** | ~600 tokens | 2× |
| `gemini_provider.py:104` (vision) | 4,096 | **1,024** | ~500 tokens | 2× |
| Discovery | 1,000 | Keep | ~200 tokens | — |
| Text parse | None set | **512** | ~300 tokens | 1.7× |

**Recipe worst-case breakdown (8 ingredients + 6 verbose steps):**
8 ingredients × `{name, amount, unit}` ≈ 96 tokens + 6 step instructions ≈ 270 tokens
+ JSON structure ≈ 60 tokens = **~430–600 tokens total**. 1,200 gives a 2× safety
margin. Starting here instead of 1,000 costs nothing (200 tokens × fractions of a cent)
but eliminates truncation risk. After Phase 3 (PostHog live), tune down using actual
p99 data if warranted.

**Vision worst-case breakdown (8 food items):**
Each `{name, quantity, unit, calories, macros: {protein, carbs, fat}}` ≈ 35 tokens × 8
= 280 tokens + top-level fields + structure ≈ 100 tokens = **~380–500 tokens total**.
Note: `MealAnalyzeFastPathPolicy.max_output_tokens = 700` already exists in code but is
NOT wired through to the generation call — the 4,096 default is always used. The fix
must pass `max_tokens=1024` explicitly in `vision_ai_service.py`'s calls to
`generate_with_vision`, not just change the provider default.

After Phase 3 observability confirms p99 stays well under the limit, tune recipe
to 1,000 and vision to 700 (the original fast_path_policy intent).

### 5.7 Fix Thinking Budget Routing (Bug 1)

**Root cause:** `MODEL_PURPOSE_MAP` in `gemini_provider.py` maps model strings
to `GeminiModelPurpose`, but there are more purposes than model strings. Both
`RECIPE_PRIMARY` and `GENERAL` map to `GeminiModelPurpose.GENERAL`, so
`thinking_budget=0` is never reached for recipes.

**Fix:** pass the original `ModelPurpose` enum value through to
`GeminiProvider.generate()` as an additional parameter, and use it directly in
`get_model_for_purpose()` instead of re-deriving from model string.

```python
# ai_model_manager.py — pass purpose_hint to provider
result = await provider.generate(
    model=model,
    purpose_hint=purpose,   # <-- new
    ...
)

# gemini_provider.py — use purpose_hint to get correct Gemini purpose
_PURPOSE_HINT_MAP = {
    ModelPurpose.RECIPE:    GeminiModelPurpose.RECIPE,
    ModelPurpose.MEAL_SCAN: GeminiModelPurpose.GENERAL,
    ModelPurpose.BARCODE:   GeminiModelPurpose.BARCODE,
    # ...
}
gemini_purpose = _PURPOSE_HINT_MAP.get(purpose_hint, GeminiModelPurpose.GENERAL)
llm = self._model_manager.get_model_for_purpose(purpose=gemini_purpose, ...)
```

### 5.8 Remove Mistral and Kimi

Both providers are removed entirely. Gemini handles all tasks via Flash and
Flash Lite. No other provider is needed.

```python
# Before
MEAL_NAMES: ["mistral-small-latest", "gemini-2.5-flash-lite", "gemini-2.5-flash"]

# After
MEAL_NAMES: ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
```

All fallback chains that reference Mistral or Kimi drop those entries.
Vision chains already have no Mistral — no change needed there.

### 5.9 PostHog LLM Analytics (OpenTelemetry)

Replace manual PostHog capture with auto-instrumented OpenTelemetry tracing.

**Packages:**
```
posthog[otel]
opentelemetry-instrumentation-langchain
```

**Init in `src/api/main.py` lifespan:**
```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from posthog.ai.otel import PostHogSpanProcessor
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

provider = TracerProvider(
    resource=Resource(attributes={SERVICE_NAME: "mealtrack-backend"})
)
provider.add_span_processor(PostHogSpanProcessor(
    api_key=os.getenv("POSTHOG_API_KEY"),
    host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
))
trace.set_tracer_provider(provider)
LangchainInstrumentor().instrument()
```

**Per-user tracking:** pass `posthog_distinct_id` via LangChain config metadata
from handlers that have the user_id in scope.

**What PostHog captures automatically (zero manual code):**
- `$ai_model`, `$ai_input_tokens`, `$ai_output_tokens`, `$ai_total_cost_usd`
- `$ai_latency`, `$ai_time_to_first_token`
- Full trace hierarchy (recipe pipeline shown as tree: phase 1 → phase 2 calls)
- Cached token accounting (explicit cache hits visible as `$ai_cached_tokens`)

**PostHog dashboards to create:**
- Daily cost by feature (recipe / scan / discovery / text_parse)
- Cost by model (Flash vs Flash Lite)
- Cache hit rate over time
- p95 latency per feature
- Tokens per call (identify prompt bloat regressions)

### 5.10 Scale: Quota Increase (not a key pool)

When approaching 10k DAU, request a Gemini quota increase via Google AI Studio
instead of building a multi-key pool. A single key at a higher tier can provide
10,000+ RPM — simpler to operate, no pool code to maintain.

---

## 6. Files Changed

### New files
| File | Purpose |
|---|---|
| `src/infra/services/ai/gemini_cache_manager.py` | Explicit context cache lifecycle |

### Modified files
| File | Change |
|---|---|
| `src/api/main.py` | Add OpenTelemetry + LangChain instrumentation init |
| `src/infra/services/ai/ai_model_manager.py` | Pass `purpose_hint`, PostHog user linking, remove Mistral/Kimi from fallback chains |
| `src/infra/services/ai/gemini_model_manager.py` | Per-purpose temperature map |
| `src/infra/services/ai/gemini_model_config.py` | Fix `PURPOSE_MODEL_DEFAULTS`, add `PURPOSE_TEMPERATURES` |
| `src/infra/services/ai/providers/gemini_provider.py` | Accept `purpose_hint`, pass `cached_content`, fix `MODEL_PURPOSE_MAP` |
| `src/domain/services/meal_suggestion/parallel_recipe_generator.py` | Use `SystemPrompts.RECIPE_GENERATION` (remove 3 inline copies) |
| `src/domain/services/meal_suggestion/recipe_attempt_builder.py` | `PARALLEL_SINGLE_MEAL_TOKENS`: 4000 → 1200 |
| `src/infra/adapters/vision_ai_service.py` | Pass `max_tokens=1024` in both `generate_with_vision` calls (currently using 4096 default); wire `fast_path_policy.max_output_tokens` |
| `src/domain/strategies/meal_analysis_strategy.py` | All 5 strategies compact; shared system prompt; remove duplicate rule constants |
| `src/infra/services/ai/prompts/system_prompts.py` | Add `RECIPE_GENERATION`, `VISION_ANALYSIS`, `DISCOVERY`, `TEXT_PARSE` (each ≥1024 tokens with few-shot examples) |
| `src/domain/services/prompts/prompt_constants.py` | Consolidate all rules here as single source of truth |
| `src/domain/services/prompts/prompt_template_manager.py` | Static/dynamic split: rules in system, variables in user message |
| `src/infra/adapters/meal_generation_service.py` | Thread `user_id` and `feature` through to `AIModelManager` |

### Deleted files
| File | Reason |
|---|---|
| `src/infra/services/ai/providers/kimi_provider.py` | Unused |
| `src/infra/services/ai/providers/mistral_provider.py` | Removed — Gemini handles all tasks |

---

## 7. Cost Impact Model

### At current scale (40 users)

| Change | Monthly saving |
|---|---|
| Fix thinking budget bug (recipe) | ~$3 |
| Recipe token limit 4000→1000 | ~$2 |
| Vision token limit 4096→1024 | ~$1 |
| Temperature fix (fewer retries) | ~$1 |
| **Total** | **~$7/month** (~58% reduction) |

### At 1M users (projected)

Assumptions: 10% DAU, avg 3 recipe taps/day, 5 meal scans/day, 2 discoveries/day.

| Change | Monthly saving |
|---|---|
| Fix thinking bug (recipe) | ~$85,000 |
| Recipe token limit 4000→1000 | ~$70,000 |
| Vision token limit 4096→1024 | ~$45,000 |
| Explicit caching (recipe system) | ~$28,000 |
| Explicit caching (vision system) | ~$18,000 |
| Temperature fix (5% fewer retries) | ~$12,000 |
| Remove Mistral/Kimi (eliminate provider overhead) | ~$5,000 |
| **Total estimated** | **~$263,000/month** |
| **Projected bill without changes** | ~$310,000/month |
| **Projected bill with changes** | ~$47,000/month |

---

## 8. Rollout Phases

### Phase 1 — Quick wins, no risk (1–2 days)
Changes that touch no prompt content, only limits and routing:
- Fix `PARALLEL_SINGLE_MEAL_TOKENS`: 4000 → 1000
- Fix vision `max_output_tokens`: 4096 → 1024
- Fix thinking budget routing bug (Bug 1)
- Add per-purpose temperature map
- Remove Mistral and Kimi providers entirely

**Deploy, monitor PostHog for error rate spike. Rollback: revert 3 constants.**

### Phase 2 — Prompt architecture (2–3 days)
- Centralise rules into `prompt_constants.py`
- Modernise 4 verbose vision strategies to compact format
- Move all rules into system messages (static/dynamic split)
- Expand system messages to ≥1024 tokens with few-shot examples
- Remove duplicate inline system strings from `parallel_recipe_generator.py`

**Deploy, watch PostHog parse failure rate. Rollback: revert prompt files.**

### Phase 3 — Observability + caching (1–2 days)
- Add OpenTelemetry + PostHog LLM Analytics (packages + `main.py` init)
- Implement `GeminiCacheManager` with background refresh
- Wire `cached_content` into `GeminiProvider`

**Verify cache hit rate in PostHog dashboard before declaring success.**

### Phase 4 — Scale infrastructure (1 day, deploy when approaching 10k users)
- Request Gemini quota increase via Google AI Studio
- Refactor `asyncio.to_thread` + `loop.run_until_complete` nesting in `MealGenerationService` to pure async (flagged as instability under load)

---

## 9. Success Metrics

| Metric | Current | Target (post Phase 2) |
|---|---|---|
| Avg output tokens / recipe call | ~3,500 | ≤1,200 (tune to ≤1,000 post-Phase 3) |
| Avg output tokens / vision call | ~3,000 | ≤1,024 (tune to ≤700 post-Phase 3) |
| Recipe 503 rate during Gemini spikes | High | Near zero (thinking disabled = shorter calls) |
| JSON parse failure rate | ~5% | ≤1% |
| Cache hit rate (Phase 3+) | 0% | ≥85% |
| Daily cost (40 users) | ~$0.40 | ≤$0.17 |

---

## 10. Open Questions

1. **Explicit cache minimum token threshold:** verify the ≥1024 system prompt
   actually hits Gemini's cache eligibility after restructure. Use `countTokens`
   API before deploying Phase 3.

2. **`asyncio.to_thread` + `loop.run_until_complete` nesting in
   `MealGenerationService`:** flagged as a potential instability under load.
   Clean up in Phase 4 — refactor to pure async when touching that file.
