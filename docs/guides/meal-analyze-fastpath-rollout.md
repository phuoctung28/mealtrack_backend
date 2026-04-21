# Meal Analyze Fast-Path Rollout Guide

This guide covers staged rollout and rollback for `/v1/meals/image` optimization.

## Feature flags

Set these environment variables:

- `MEAL_ANALYZE_RUNTIME_POLICY_ENABLED` (default: `true`)
- `MEAL_ANALYZE_CANARY_PERCENT` (default: `100`, range: `0..100`)
- `MEAL_ANALYZE_OPTIMIZED_PROMPT_ENABLED` (default: `true`)
- `MEAL_ANALYZE_STRICT_SCHEMA_MODE` (default: `true`)
- `MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH` (default: `false`)

## Canary rollout

1. Start with `MEAL_ANALYZE_CANARY_PERCENT=10`.
2. Watch p95 latency and parse failure rate for `/v1/meals/image`.
3. Increase to `25`, `50`, then `100` when metrics remain stable.
4. Keep `MEAL_ANALYZE_RUNTIME_POLICY_ENABLED=true` during rollout.

User assignment is deterministic by user ID hash, so users stay in the same cohort.

## Regression gates

CI includes:

1. Prompt-eval gate: `scripts/development/evaluate_meal_analyze_prompt_candidates.py`
2. Unit tests for parser compatibility, prompt flags, and canary policy behavior.

## Rollback

For immediate rollback, set:

- `MEAL_ANALYZE_RUNTIME_POLICY_ENABLED=false`
- `MEAL_ANALYZE_OPTIMIZED_PROMPT_ENABLED=false`
- `MEAL_ANALYZE_STRICT_SCHEMA_MODE=false`
- `MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH=true`

This restores legacy behavior and bypasses fast-path policy.
