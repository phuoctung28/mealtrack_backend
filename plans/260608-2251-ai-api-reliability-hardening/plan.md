---
title: AI API reliability hardening
description: >-
  Fix AI API fallback, error semantics, payload validation, and route-test
  reliability
status: completed
priority: P2
branch: codex/ai-api-reliability-hardening
tags:
  - ai
  - reliability
  - fastapi
  - gemini
blockedBy: []
blocks: []
created: '2026-06-08T15:51:35.166Z'
createdBy: 'ck:plan'
source: skill
---

# AI API reliability hardening

## Overview

Harden the AI-facing API boundary after review findings around Gemini cache fallback, image analysis error mapping, ingredient payload validation, dormant image-url analysis, and route-test setup. This plan keeps existing public success response shapes stable while making provider outages observable and retryable.

Expected output: a focused PR on `codex/ai-api-reliability-hardening` with code, tests, docs/plan notes, and a passing focused verification suite.

Acceptance criteria:
- Parse-text JSON recovery keeps passing and remains shared by Gemini provider extraction.
- Cache-enabled Gemini fallback never passes a cache created for a different model.
- `/v1/meals/image/analyze` returns `AI_UNAVAILABLE` 503 for provider outage and still returns `NOT_FOOD_IMAGE` for real validation failures.
- Ingredient recognition rejects oversized or invalid base64 payloads before expensive decode work.
- The registered image-by-URL command analyzes actual fetched image bytes or fails with a clear validation/runtime error.
- AI route-level tests can run against Postgres test setup.
- No DB schema, auth, or successful public response-shape change.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Research and design](./phase-01-research-and-design.md) | Completed |
| 2 | [Implement reliability fixes](./phase-02-implement-reliability-fixes.md) | Completed |
| 3 | [Verify and ship](./phase-03-verify-and-ship.md) | Completed |

## Dependencies

- Existing Redis cache strategy plan is completed and does not block this work.
- Existing docs/specs confirm Gemini cache and vision fallback were previously added for cost and resilience; this plan narrows their failure modes instead of redesigning AI architecture.

## Scope Boundary

In scope:
- AI model manager cache/fallback behavior.
- Gemini cache metadata stored in Redis.
- Vision service exception preservation and image URL byte handling.
- Ingredient recognition request/handler validation.
- Focused unit/API tests and Postgres test harness syntax.

Out of scope:
- New AI provider integrations.
- New DB migrations.
- Reworking meal suggestion recipe partial-failure product behavior.
- Full prompt or nutrition pipeline redesign.

## Red-Team Notes

- Risk: changing cache storage format could invalidate old Redis values. Mitigation: support legacy string values as model-unknown caches and only use them when model metadata matches or cache is omitted.
- Risk: preserving `AIUnavailableError` through vision may alter mobile error UX from 400 to 503. This is intended because outage is not a bad image.
- Risk: fetching image URLs could create SSRF exposure. Mitigation: only allow HTTP(S), enforce response status/content type/size, and keep the existing provider byte path.
- Risk: route-test setup may reveal broader database assumptions. Mitigation: fix only PostgreSQL-compatible database creation syntax and keep test schema setup unchanged.
