---
title: "Structured Vision Reliability, Retry Budgets, and AI Observability"
description: "Rework meal image analysis around schema-valid provider success, bounded retry policy, Cloudflare/Gemini rollout gates, and Sentry/PostHog AI metrics."
status: done
priority: P1
effort: "2-3 days"
branch: "main"
tags: [backend, ai, langchain, cloudflare, vision, reliability, observability]
blockedBy: []
blocks: []
created: "2026-06-23T02:54:55.741Z"
createdBy: "ck:plan"
source: skill
---

# Structured Vision Reliability, Retry Budgets, and AI Observability

## Overview

Make meal image analysis reliable enough for production traffic. Current logs show repeated `[JSON-EXTRACT-FAILED]` and 30-38s `503` responses because the normal success path still depends on raw model text, the outer meal analyzer can retry the whole provider chain, and observability does not cleanly answer which provider, model, retry, or validation stage failed.

This plan changes the success contract: a provider call is successful only when output validates against the meal-vision schema and is normalized for the existing parser/service path. Raw JSON extraction becomes a last-resort fallback. Retry behavior becomes failure-kind aware and time-budgeted. Operational metrics go through the existing `src.observability` facade into Sentry logs/metrics; PostHog remains useful for existing LangChain/LLM traces and product analytics, not the primary alerting surface.

Acceptance criteria:
- Schema covers the prompt-required image response shape and preserves backend-derived calories as source of truth.
- Gemini vision uses LangChain/Gemini structured output before raw parsing.
- Cloudflare vision uses direct Workers AI REST only behind a contract/canary gate; do not rely on `langchain-cloudflare` for image input.
- Retry policy separates transient provider failures, timeout, schema validation failure, parser failure, and no-food analysis.
- Image analysis has Sentry-safe metrics/logs for request, provider attempt, latency, fallback, retry, timeout, parse failure, and validation failure.
- Focused parser, provider, model-manager, vision-service, and route smoke tests pass with `uv run`.

Mode: TDD-style hard plan. Reason: critical AI user flow, existing tests, provider behavior risk.

Hard-mode decisions:
- Sentry is the operational dashboard/alerting path because the repo already has `src.observability`, Sentry logs, and Sentry metrics wiring. Do not add a new dashboard dependency.
- PostHog is kept for existing OpenTelemetry/LangChain AI analytics and product funnels. It can help with model latency/cost trends, but it should not own user-impacting error alerts.
- Cloudflare-first production routing is allowed only after schema-valid canary data. Until then, prefer Gemini structured output as the reliability baseline and use Cloudflare as gated/canary or fallback per env policy.
- Do not log raw model responses, prompts, image bytes/base64, image URLs, or user food descriptions.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Schema Contract](./phase-01-schema-contract.md) | Done |
| 2 | [Structured Provider Output](./phase-02-structured-provider-output.md) | Done |
| 3 | [Retry Budget and Failure Classification](./phase-03-retry-budget-and-failure-classification.md) | Done |
| 4 | [AI Observability Dashboard and Rollout](./phase-04-ai-observability-dashboard-and-rollout.md) | Done |

## Dependencies

- No direct dependency on pending `260612-1046-service-initiated-bandwidth-reduction`; this plan touches AI provider parsing, not Cloudinary upload flow.
- Must preserve current uncommitted parser-fallback work in `src/infra/adapters/ai_json_utils.py` and `tests/unit/infra/adapters/test_ai_json_logging.py`.
- Must preserve current `AIProviderPort` and clean architecture direction: domain schema is provider-independent; infra owns LangChain, Cloudflare REST, Sentry, and PostHog.
- External references:
  - LangChain structured output: https://docs.langchain.com/oss/python/langchain/structured-output
  - LangChain Google GenAI structured output: https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai
  - LangChain Cloudflare feature matrix: https://docs.langchain.com/oss/python/integrations/chat/cloudflare_workersai
  - Cloudflare Workers AI JSON mode: https://developers.cloudflare.com/workers-ai/features/json-mode/
  - Gemini structured output: https://ai.google.dev/gemini-api/docs/structured-output
  - Sentry Python metrics: https://docs.sentry.io/platforms/python/metrics/
  - PostHog AI observability: https://posthog.com/docs/ai-observability/installation/langgraph

## Red-Team Review

- Risk: schema-only output still returns plausible but wrong nutrition. Mitigation: schema validates shape only; existing downstream nutrition/macros validation and derived-calorie rules remain required.
- Risk: retries improve success rate but worsen p95 latency. Mitigation: retry only transient/provider errors and enforce request-level wall-time budget.
- Risk: Sentry metrics become high-cardinality or privacy-sensitive. Mitigation: add only allowlisted low-cardinality tags and content-length buckets, never raw content.
- Risk: Cloudflare model is cheaper/faster but less schema-reliable. Mitigation: canary by env, compare schema-valid success rate and p95 before making it primary.
