# Meal Image Analyze Performance Design

Date: 2026-04-20  
Scope: `/v1/meals/image` latency-first optimization (p95 <= 6s) with concrete runtime reductions

## 1. Goal

Reduce end-to-end latency for meal image analysis while preserving current API behavior and analysis quality guardrails.

## 2. Confirmed decisions

1. Optimize `/v1/meals/image` first.
2. `/v1/meals/image/analyze-url` is being deprecated; only compatibility maintenance, no new optimization investment.
3. Prioritize latency first with target p95 <= 6s for successful `/v1/meals/image` responses.
4. Use Pydantic-based schema hardening in phase 2 (after baseline metrics).
5. Repo-native-first optimization workflow (no external observability/optimization stack in initial rollout).

## 3. Current flow (as implemented)

`UploadMealImageImmediatelyHandler` performs:
1. Upload image + create `Meal` with `ANALYZING`.
2. Vision AI call (`phase 1`).
3. Parse AI output to nutrition/dish/emoji.
4. Optional translation (`phase 2`) for non-English language.
5. Save final meal + return response.

Current logs include phase timing markers but are not normalized into a consistent metric schema.

## 4. Proposed architecture (Fast-path pipeline)

Keep synchronous endpoint contract, but enforce a bounded and deterministic critical path:

1. **Persist step:** upload + create meal record.
2. **AI step:** single bounded vision call under low-latency policy.
3. **Parse/validate step:** strict parse path with typed error categories.
4. **Finalize step:** persist + return.

### Fast-path principles

1. No unbounded retries.
2. Non-essential work removed from critical path where possible (notably translation).
3. Strict stage budgets (timeout + token budget + fallback policy).
4. Structured observability for each stage.

## 4.1 Concrete phase-1 optimizations (not just monitoring)

These are required implementation actions for phase 1:

1. **Prompt compression for scan**  
   Replace verbose scan prompt with a compact, strict-output prompt that only asks for fields used by parser/output contract.

2. **Output-size reduction**  
   Cap returned `foods` list (e.g., top-N most relevant ingredients), trim unnecessary prose fields, and enforce concise dish naming.

3. **Hard AI budget profile**  
   Apply strict per-request limits in `VisionAIService` for scan:
   - low output token cap,
   - hard timeout,
   - deterministic generation settings for lower variance.

4. **Single retry policy**  
   At most one retry only for transient failures, with reduced budget on retry.

5. **Translation off critical path**  
   Keep non-English translation out of p95 path in phase 1; if needed, perform asynchronously after successful meal save.

6. **Fail-fast non-food path**  
   Return controlled non-food failure quickly when parse signal is below threshold; do not spend extra retry budget on likely non-food input.

## 5. Component-level design

## 5.1 `upload_meal_image_immediately_command_handler.py`

Introduce explicit stage policy wiring:
- `phase1` (vision): timeout + retry budget + token budget profile.
- `phase2` (translation): excluded from p95-critical path in phase 1 rollout.
- normalized structured log payload at each stage.

No behavior change to endpoint contract or error mapping semantics unless explicitly covered by typed failure categories below.

## 5.2 `vision_ai_service.py`

Add low-latency invocation profile for meal analyze:
- deterministic generation profile for scan task,
- explicit output budget,
- explicit timeout handling surface,
- consistent response contract for parser layer.

Latency profile target (initial):
- normal attempt timeout: 2.5s
- retry timeout: 1.5s
- max attempts: 2 total
- token budget tuned for compact JSON-only output

## 5.3 Parser layer (phase 2)

Move from permissive dict parsing to Pydantic output models:
- `VisionAnalyzeResponse`
- `FoodItemResponse`
- `MacrosResponse`

Validation constraints:
- required fields for dish + foods + macro primitives,
- numeric bounds (non-negative),
- explicit schema violation errors,
- explicit distinction between schema failure and non-food detection.

## 5.4 Minimal metrics envelope (supporting, not primary work)

For each request/stage, log:
- `flow_type=meal_image_analyze`
- `endpoint=/v1/meals/image`
- `stage` (`upload`, `vision`, `parse`, `persist`)
- `elapsed_ms`
- `model`
- `token_budget`
- `retry_count`
- `fallback_used`
- `result` (`success|failure`)
- `failure_type` (if any)

## 6. Error handling model

Typed failure categories:
1. `vision_timeout`
2. `vision_empty_or_blocked`
3. `schema_validation_failed`
4. `not_food_detected`
5. `persistence_failed`

Policy:
- at most one bounded retry for transient vision failures,
- fail fast after retry budget exhausted,
- keep API-facing error behavior stable for non-food and analysis failures.

## 7. Testing and performance verification

## 7.1 Baseline and regression benchmarks

Add benchmark runner and fixtures for `/v1/meals/image`:
- representative food images,
- non-food images,
- multilingual request headers.

Track:
- p50/p95 latency,
- fallback/retry rate,
- parse success rate.

Gate:
- reject changes that regress p95 above target or reduce parse success below threshold.

## 7.2 Functional guardrails

Golden checks for:
- food decomposition correctness,
- macro sanity consistency,
- non-food rejection behavior,
- parser schema validity (phase 2 onward).

## 8. Rollout plan

1. Feature-flag fast-path policy.
2. Canary rollout to limited traffic.
3. Observe p95 and failure-category drift.
4. Auto-rollback on sustained p95 regression or error-rate spike.

## 9. Out of scope (this design cycle)

1. Full optimization of meal generation endpoints.
2. External observability platforms (Langfuse/LangSmith/PromptLayer) in initial rollout.
3. New functionality for deprecated `/analyze-url`.

## 10. Follow-up after stabilization

Apply the same framework to meal generation (`/v1/meal-suggestions/*`):
- KPI instrumentation,
- schema hardening,
- prompt optimization loop,
- runtime policy tuning.
