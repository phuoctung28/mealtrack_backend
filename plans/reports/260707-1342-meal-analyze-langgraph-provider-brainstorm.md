---
type: brainstorm-report
status: approved
created: 260707-1342
source: ck:brainstorm
topic: meal analyze langgraph provider architecture
---

# Meal Analyze LangGraph Provider Brainstorm

## Summary

Approved direction: use LangGraph as a deterministic internal workflow for the
meal image analysis family while preserving the current synchronous API
contract.

Do not convert image analysis to background `PROCESSING` in this round. Do not
add `READY_WITH_WARNINGS` as a persisted meal status in Sprint 1. Do not let
graph nodes call OpenAI, Cloudflare, FatSecret, USDA, OpenFoodFacts, Sentry, or
raw SQL directly.

## Requirements

Expected output:
- A future implementation plan for a sync-compatible LangGraph workflow.
- Coverage for all meal image entrypoints:
  - `POST /v1/meals/image/analyze`
  - `POST /v1/meals/scan-by-url`
  - `POST /v1/meals/food-label/scan-by-url`

Acceptance criteria:
- Existing response shape remains `DetailedMealResponse`.
- Successful scans still return a READY meal synchronously.
- Direct upload and scan-by-url use the same workflow behavior for plated meals.
- Food-label scan uses the same workflow shell but keeps label-specific parsing.
- Vision providers remain behind `VisionAIService` and `AIModelManager`.
- FatSecret validates nutrition references only; it does not identify images.
- Backend remains calorie authority from macros.
- Provider failures degrade safely to old behavior or controlled validation errors.

Out of scope for Sprint 1:
- Generic chat agent.
- Background graph execution.
- New mobile polling flow.
- New persisted `READY_WITH_WARNINGS` status.
- USDA and OpenFoodFacts expansion unless already needed by existing food-label or barcode code.
- Meal insight subgraph.
- DeepL changes beyond current translation behavior.
- PostHog product analytics expansion.
- New provider-payload cache table.

## Scout Findings

Repo stack:
- FastAPI / Python 3.13.
- LangChain already installed.
- LangGraph not currently installed.
- CQRS command handlers and PyMediator are the live handler boundary.

Current image-analysis shape:
- `/v1/meals/image/analyze` sends `UploadMealImageImmediatelyCommand`.
- Handler uploads image, runs vision, parses nutrition, persists READY meal, then returns.
- `scan-by-url` downloads Cloudinary bytes and follows a parallel persistence path.
- `food-label/scan-by-url` uses `FoodLabelImageAnalysisStrategy` and label-specific parser.

Current provider shape:
- `VisionAIService` is the shared vision adapter.
- `AIModelManager` owns provider fallback.
- OpenAI is base vision provider; Cloudflare Workers AI can be appended as vision fallback.
- FatSecret exists but current `search_foods()` enriches each search result with `food.get.v5`, which is too expensive for image validation if used raw.

Current persistence shape:
- `food_reference` already stores canonical per-100g nutrition and source metadata.
- Existing meal status enum does not include `READY_WITH_WARNINGS`.

## Approaches Considered

### Approach A: Full downloaded plan

Add LangGraph, subgraphs, new provider ports, FatSecret validation, new tables,
new statuses, insight, DeepL, USDA, OpenFoodFacts, Sentry metrics, and PostHog
analytics across two sprints.

Pros:
- Complete target architecture.
- Strong provider-role separation.
- Future-ready for parse-text and meal suggestion reuse.

Cons:
- Too much blast radius for the highest-traffic scan path.
- Background-processing section conflicts with current sync API behavior.
- New DB tables before match quality is proven.
- `READY_WITH_WARNINGS` requires domain, DB, API, and mobile status alignment.

Verdict: good north star, not the first implementation slice.

### Approach B: Sync graph wrapper plus optional FatSecret validation

Add an app-layer LangGraph workflow behind a feature flag. Route direct upload,
scan-by-url, and food-label scan through one workflow interface. Keep existing
vision, parser, UoW, translation, and response contracts. Add optional FatSecret
reference validation for plated meal scans after vision output.

Pros:
- Preserves current mobile/API behavior.
- Lets graph orchestration be tested without provider rewrite.
- Reuses existing Clean Architecture boundaries.
- Gives a safe rollout path and rollback flag.
- Supports all meal image entrypoints together.

Cons:
- Less glamorous than the full graph architecture.
- Some duplicate handler code must be extracted carefully.
- FatSecret validation will initially be conservative and may not improve every scan.

Verdict: recommended.

### Approach C: No LangGraph yet; extract plain Python workflow service

Create a `MealAnalyzeWorkflowService` with normal Python methods and no
LangGraph dependency. Add LangGraph later only when branching/state complexity
requires it.

Pros:
- Smallest diff.
- Lowest dependency and debugging risk.
- Fits current sync handler shape.

Cons:
- Does not satisfy the requested LangGraph architecture direction.
- Later migration may duplicate work.
- Less node-level observability than an explicit graph.

Verdict: viable fallback if LangGraph adds friction, but not the approved path.

## Final Recommendation

Use Approach B.

Create a sync-compatible `meal_analyze_graph` in the application layer. Treat
LangGraph as deterministic workflow plumbing, not as an autonomous agent.

Recommended module shape:

```text
src/app/graphs/meal_analyze/
  __init__.py
  state.py
  graph.py
  nodes.py
  quality_gate.py
  services.py
```

Keep provider adapters where they are:

```text
src/infra/adapters/vision_ai_service.py
src/infra/services/ai/ai_model_manager.py
src/infra/adapters/fat_secret_service.py
```

Add or evolve app/domain services only where they preserve boundaries:

```text
src/app/services/meal_analyze_workflow.py
src/app/services/food_reference_validation_service.py
src/domain/ports/nutrition_reference_provider_port.py
```

Sprint 1 workflow:

```text
prepare_image
  -> select_strategy
  -> run_vision_analysis
  -> parse_and_validate_nutrition
  -> optional_reference_validation
  -> persist_ready_meal
  -> emit_safe_observability
```

Food-label workflow:

```text
prepare_image
  -> select_food_label_strategy
  -> run_vision_analysis
  -> parse_food_label_nutrition
  -> persist_ready_food_label_meal
  -> emit_safe_observability
```

## Database Decision

Start with reuse: no new DB tables in Sprint 1.

Use `food_reference` for local reference matches first. Add a staged FatSecret
search/detail method that can validate a selected candidate without fetching
details for every search result.

Only add `external_food_mappings` after proving all are true:
- Multiple FatSecret matches need durable disambiguation.
- User-specific selection history improves future scans.
- Existing `food_reference` cannot safely represent the relationship.

Only add `external_food_payload_cache` after proving all are true:
- Provider latency/cost is material in production traces.
- FatSecret agreement allows the specific cached payload and TTL.
- Cache invalidation and privacy rules are documented.

## Feature Flags

Minimum flags:

```text
AI_MEAL_ANALYZE_GRAPH_ENABLED=false
AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED=false
AI_MEAL_ANALYZE_EXTERNAL_PROVIDER_TIMEOUT_SECONDS=5
AI_MEAL_ANALYZE_GRAPH_VERSION=v1
```

Existing provider flags remain source of truth for OpenAI and Cloudflare routing.

## Risks

Graph abstraction overfit:
- Mitigation: keep nodes coarse. Do not turn every helper into a node.

Handler duplication:
- Mitigation: extract only shared input/result orchestration. Preserve current route contracts.

FatSecret wrong match:
- Mitigation: local verified match wins, conservative score threshold, fallback to AI estimate with source marker.

Provider latency:
- Mitigation: short timeout, staged detail fetch, feature flag, no hard dependency.

Status contract drift:
- Mitigation: no new meal status in Sprint 1. Warnings can be internal metrics/logs first.

Privacy:
- Mitigation: no raw image bytes, raw image URLs, raw provider payloads, raw AI output, prompts, auth headers, emails, or food payloads in logs/metrics.

## Validation Criteria

Unit tests:
- Graph disabled path preserves current handler behavior.
- Graph enabled path returns equivalent READY meal for direct upload.
- Graph enabled path returns equivalent READY meal for scan-by-url.
- Food-label path keeps label-specific parser and metadata.
- FatSecret disabled path never calls FatSecret.
- FatSecret timeout degrades without failing an otherwise valid scan.
- Staged FatSecret search does not call `food.get.v5` for every result.
- Domain layer does not import LangGraph.
- Graph nodes do not import vendor SDKs or `sentry_sdk`.

Focused commands:

```bash
uv run pytest tests/unit/handlers/command_handlers/test_upload_meal_image_immediately_command_handler.py -q
uv run pytest tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py -q
uv run pytest tests/unit/infra/adapters/test_fat_secret_service.py -q
uv run pytest tests/unit/architecture -q --import-mode=importlib
```

Broader pre-push gate:

```bash
uv run pytest
ruff check src tests
```

## Next Step

Recommended next mode: `/ck:plan --tdd`.

Reason: this touches critical meal image behavior, multiple route/handler
entrypoints, provider fallback, and nutrition correctness. TDD-style planning
should lock current sync behavior before introducing graph routing.

Use this report as plan input:

```text
plans/reports/260707-1342-meal-analyze-langgraph-provider-brainstorm.md
```

## Unresolved Questions

None. User approved sync-compatible graph direction, all meal image entrypoints,
and reuse-first DB posture.
