# Meal Analyze Fast-Path Rollout Guide

This guide covers staged rollout and rollback for `/v1/meals/image` optimization.

## Feature flags

Set these environment variables:

- `MEAL_ANALYZE_RUNTIME_POLICY_ENABLED` (default: `true`)
- `MEAL_ANALYZE_CANARY_PERCENT` (default: `100`, range: `0..100`)
- `MEAL_ANALYZE_OPTIMIZED_PROMPT_ENABLED` (default: `true`)
- `MEAL_ANALYZE_STRICT_SCHEMA_MODE` (default: `true`)
- `MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH` (default: `false`)
- `AI_MEAL_ANALYZE_GRAPH_ENABLED` (default: `false`)
- `AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED` (default: `false`)
- `AI_MEAL_ANALYZE_EXTERNAL_PROVIDER_TIMEOUT_SECONDS` (default: `5`)
- `AI_MEAL_ANALYZE_GRAPH_VERSION` (default: `v1`)

The graph flags are independent of provider routing. OpenAI and Cloudflare
vision order remains owned by `AIModelManager`.

When the graph is enabled, meal value insights are scheduled by the app-layer
graph after READY meal persistence and meal cache invalidation. Graph-disabled
API routes keep the legacy scheduling fallback. Both paths use the same app-layer
scheduler, include compact user profile context when available, and never block
READY meal responses.

## Canary rollout

1. Keep `AI_MEAL_ANALYZE_GRAPH_ENABLED=false` in baseline production.
2. Enable `AI_MEAL_ANALYZE_GRAPH_ENABLED=true` with
   `AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED=false`.
3. Watch p95 latency, provider failure rate, no-food rejection rate, and READY
   meal creation rate for `/v1/meals/image/analyze`,
   `/v1/meals/scan-by-url`, and `/v1/meals/food-label/scan-by-url`.
   Also watch meal value insight cache/generation logs for profile-aware cache
   key churn after profile updates and duplicate same-request scheduling.
4. After graph-only behavior is stable, canary
   `AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED=true`.
5. Keep `MEAL_ANALYZE_RUNTIME_POLICY_ENABLED=true` during rollout.

User assignment is deterministic by user ID hash, so users stay in the same cohort.

## Regression gates

CI includes:

1. Prompt-eval gate: `scripts/development/evaluate_meal_analyze_prompt_candidates.py`
2. Unit tests for parser compatibility, prompt flags, and canary policy behavior.

## Rollback

For immediate rollback, set:

- `AI_MEAL_ANALYZE_GRAPH_ENABLED=false`
- `AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED=false`
- `MEAL_ANALYZE_RUNTIME_POLICY_ENABLED=false`
- `MEAL_ANALYZE_OPTIMIZED_PROMPT_ENABLED=false`
- `MEAL_ANALYZE_STRICT_SCHEMA_MODE=false`
- `MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH=true`

This restores legacy handler behavior and bypasses fast-path policy. FatSecret
validation is optional reference validation only; disabling it must not block
valid image scans.

If graph scheduling fails or lacks optional scheduler dependencies, the graph
records `meal_value_insight_scheduled=false`, returns the READY meal, and leaves
`GET /v1/meals/{meal_id}/value-insights` available for compatibility refresh.
