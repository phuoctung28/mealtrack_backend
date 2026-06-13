---
title: "Production Logging Severity and Privacy Cleanup"
description: "Normalize MealTrack production log levels and redact risky log content before expanding log ingestion."
status: completed
priority: P1
effort: "2-3 days"
branch: "delivery"
tags: [backend, observability, logging, security, refactor]
blockedBy: []
blocks: []
created: "2026-06-13T06:19:17.032Z"
createdBy: "ck:plan"
source: skill
mode: tdd
brainstorm: "../reports/260613-1313-application-logging-strategy-audit.md"
---

# Production Logging Severity and Privacy Cleanup

## Overview

Implement the approved logging audit cleanup with tests first. The goal is not a
logging-platform rewrite; it is a targeted production hardening pass that:

- normalizes INFO/WARNING/ERROR/CRITICAL semantics,
- removes high-risk raw content from logs,
- preserves the existing Sentry observability facade boundary,
- hardens production logs after the Sentry Logs/Metrics/Profile work already
  present in the worktree.

Expected output: code, tests, and docs that make production logs useful without
leaking emails, raw image URLs, raw AI output, request bodies, auth data, or raw
provider payloads.

## Scope Challenge

- Existing code: request middleware, Sentry facade, safe context filters, Sentry
  docs, cron logging, and focused middleware/monitoring tests already exist.
- Minimum changes: request severity matrix, P0/P1 redaction, CRITICAL policy for
  core startup/readiness failures, docs/tests. No structlog or JSON rewrite.
- Complexity: touches several hotspots but one concern. Five TDD phases keep
  regression coverage clear and avoid one giant logging churn pass.
- Selected mode: HOLD SCOPE with `--tdd`.

## Requirements

Acceptance criteria:

- Expected 400/401/403/404 responses do not log at WARNING by default.
- 429, invalid webhook authorization, slow responses, retry/degrade paths remain
  WARNING.
- 5xx/unhandled exceptions still log ERROR and remain eligible for Sentry issues.
- CRITICAL appears only on page-worthy core-failure paths.
- Representative logs do not include emails, raw image URLs, raw AI response
  snippets, auth tokens, request bodies, or raw provider payloads.
- `rg "import sentry_sdk|sentry_sdk\\." src` still only matches
  `src/infra/monitoring/sentry.py`.
- Existing Sentry Logs/Metrics/Profile behavior remains compatible and safer after
  redaction cleanup.

Out of scope:

- Replacing stdlib logging with structlog/loguru/JSON logging.
- Broad migration of every f-string logger call.
- Product analytics or audit-event redesign.
- Sentry alert/dashboard API automation.
- Premium/admin entitlement changes.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Regression Guards](./phase-01-regression-guards.md) | Completed |
| 2 | [Request Severity Policy](./phase-02-request-severity-policy.md) | Completed |
| 3 | [Sensitive Log Redaction](./phase-03-sensitive-log-redaction.md) | Completed |
| 4 | [Critical Startup Boundaries](./phase-04-critical-startup-boundaries.md) | Completed |
| 5 | [Documentation and Verification](./phase-05-documentation-and-verification.md) | Completed |

## Dependencies

- Source audit: `plans/reports/260613-1313-application-logging-strategy-audit.md`
- Completed prerequisite: `plans/260613-1239-sentry-observability-connector/plan.md`
- Related completed ingestion expansion:
  `plans/260613-1308-sentry-logs-metrics-profiles/plan.md`
- Coordinate only, no hard block:
  `plans/260612-1046-service-initiated-bandwidth-reduction/plan.md` may touch
  Cloudinary/upload files.

## Validation

Focused gates:

- `./.venv/bin/python -m pytest tests/unit/api/middleware/test_request_logger.py tests/unit/api/test_api_main_firebase_and_lifespan.py tests/unit/infra/adapters/test_resend_email_adapter.py tests/unit/infra/adapters/test_vision_ai_service.py tests/unit/infra/adapters/test_ai_json_logging.py tests/unit/infra/test_cloudinary_image_store.py tests/unit/handlers/command_handlers/test_upload_image_consistency.py tests/unit/api/test_webhook_handler.py -q`
- `rg "import sentry_sdk|sentry_sdk\\." src`
- `rg "https://res.cloudinary.com|content\\[:500\\]|Email sent to|Failed to send email to" src tests`
- `./.venv/bin/python -m ruff check <touched python files>`
- `./.venv/bin/python -m py_compile <touched runtime python files>`

Release gates:

- `ruff check src tests`
- `mypy src`
- `pytest`
