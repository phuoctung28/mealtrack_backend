---
phase: 4
title: "AI Observability Dashboard and Rollout"
status: pending
priority: P1
effort: "1 day"
dependencies: [2, 3]
---

# Phase 4: AI Observability Dashboard and Rollout

## Overview

Make image-analysis reliability visible in production. Use the existing `src.observability` facade and Sentry connector for operational logs, metrics, alerts, and dashboards. Keep PostHog for existing OpenTelemetry/LangChain AI analytics and product funnels.

## Context Links

- `src/observability.py`
- `src/observability_connectors.py`
- `src/infra/monitoring/sentry.py`
- `src/infra/adapters/posthog_adapter.py`
- `src/api/main.py`
- `src/infra/services/ai/ai_model_manager.py`
- `docs/external-services.md`
- Sentry Python metrics/logs docs
- PostHog AI observability docs

## Key Insights

- The repo already has Sentry logs/metrics support through `src.observability`; do not bypass it with direct SDK calls scattered across providers.
- `observability_connectors.py` safe attribute allowlist lacks several AI-specific low-cardinality keys.
- `src/api/main.py` already instruments LangChain with PostHog OpenTelemetry when `POSTHOG_API_KEY` is set.
- The missing piece is operational AI reliability metrics by provider/model/failure kind and a rollout dashboard.

## Requirements

- Functional: emit metrics for request count, success/failure, provider attempt, provider latency, retry, fallback, parse failure, schema validation failure, timeout, and circuit open.
- Functional: emit safe structured logs that can answer which provider/model/stage failed for a request.
- Functional: document a Sentry dashboard/alert checklist and PostHog secondary analysis use.
- Functional: define Cloudflare canary rollout gates based on schema-valid success rate and p95 duration.
- Non-functional: all attributes must be low-cardinality and privacy-safe.
- Non-functional: no raw model response, prompt, image URL, image bytes/base64, or user food text in logs/metrics.

## Architecture

Instrumentation locations:

1. Upload handler: request-level duration, final status, attempt count.
2. `AIModelManager`: provider attempt, fallback, circuit state, classified failure kind.
3. Providers: provider latency, schema success/failure, parser fallback use.
4. `ai_json_utils`: parse-failure counters with content-length bucket only.

Dashboard source decision:

- Primary: Sentry logs/metrics for incident response, alerts, and operational dashboard.
- Secondary: PostHog AI observability for LangChain traces, model/cost trends, and product funnel correlation.

## Related Code Files

- Modify: `src/observability_connectors.py`
- Modify: `src/infra/services/ai/ai_model_manager.py`
- Modify: `src/infra/services/ai/providers/gemini_provider.py`
- Modify: `src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`
- Modify: `src/infra/adapters/ai_json_utils.py`
- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Modify: `docs/external-services.md`
- Modify: focused observability/provider tests

## Implementation Steps

### Tests Before

1. Add tests that provider attempts emit metric/log calls with safe fields.
2. Add tests that parse/schema failures emit counters without raw content.
3. Add tests that allowlisted AI attributes survive sanitization and high-cardinality fields are dropped.
4. Add tests that upload handler emits request-level duration/final status.

### Metrics

Emit these through `src.observability`:

- `ai.vision.request.count`
- `ai.vision.request.duration_ms`
- `ai.vision.provider.attempt.count`
- `ai.vision.provider.latency_ms`
- `ai.vision.retry.count`
- `ai.vision.fallback.count`
- `ai.vision.parse_failure.count`
- `ai.vision.schema_validation_failure.count`
- `ai.vision.timeout.count`
- `ai.vision.circuit_open.count`

### Refactor

1. Extend safe attribute allowlist with low-cardinality AI keys: `ai_provider`, `ai_model`, `ai_purpose`, `ai_stage`, `failure_kind`, `error_code`, `attempt_index`, `fallback_from`, `fallback_to`, `content_len_bucket`.
2. Add metrics/log events at the four instrumentation locations.
3. Bucket content lengths instead of emitting exact raw response size if cardinality becomes noisy.
4. Add docs section with Sentry dashboard panels and alert thresholds.
5. Add Cloudflare rollout gates:
   - canary enabled by env only
   - schema-valid success rate at or above Gemini baseline
   - p95 request duration below agreed threshold
   - parse/schema failure rate below alert threshold
   - one-command rollback to Gemini-first/provider-disabled config

### Tests After

1. Run observability connector tests.
2. Run AI model manager tests.
3. Run provider tests.
4. Run parser logging tests.
5. Run docs/lint checks if docs changed.

## Success Criteria

- [ ] Sentry dashboard can show image-analysis success rate, 503 rate, p95/p99 duration, provider success rate, parse/schema failures, retries, fallbacks, and circuit opens.
- [ ] PostHog remains wired for LLM traces/product correlation without replacing Sentry operational metrics.
- [ ] All emitted attributes are allowlisted and privacy-safe.
- [ ] Cloudflare primary routing requires canary evidence, not just model availability.
- [ ] Docs explain where to look during a production image-analysis incident.

## Risk Assessment

Risk: dashboard metrics are too noisy or too expensive. Mitigation: emit counters/distributions at stage boundaries, not every internal helper; keep tag set small.

Risk: exact model IDs create moderate cardinality. Mitigation: model set is controlled by config; keep raw response IDs/request IDs out of metric tags.

Risk: PostHog and Sentry numbers disagree. Mitigation: define Sentry as source of truth for operational failure rate and PostHog as trace/product analysis.

## Security Considerations

Do not log raw AI content, image bytes/base64, signed URLs, prompts, Firebase claims, or food descriptions. Avoid user ID tags unless existing request context already hashes/sanitizes them.
