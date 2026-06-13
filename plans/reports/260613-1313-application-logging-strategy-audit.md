---
type: brainstorm-report
date: 2026-06-13
topic: application logging strategy audit
status: draft
source: ck:brainstorm
scope: docs-only
---

# Application Logging Strategy Audit

## Summary

MealTrack already has useful logging primitives: request middleware, Sentry facade,
safe observability context, cron logs, and many service-level logs. The problem is
not missing logs. The problem is inconsistent severity, too much call-site freedom,
and several logs that risk leaking user/provider content or creating noisy alerts.

Recommendation: keep Python stdlib logging, keep Sentry behind the existing
observability facade, and standardize a small production taxonomy:

| Production level | Use for | Alert behavior |
| --- | --- | --- |
| INFO | Normal milestones and completed operations | No alert |
| WARNING | Unexpected but non-breaking degradation or retry | Dashboard, trend review |
| ERROR | User-impacting functional failure requiring engineering attention | Sentry issue |
| CRITICAL | Service/core dependency unusable or health-check failure | Page/on-call |

DEBUG remains allowed for local/dev diagnosis, but production default should hide
it. Prefer `logger.critical(...)` over `logger.fatal(...)` in code because
`CRITICAL` is the stdlib canonical name.

## Scout Findings

- Stack: FastAPI 0.115+, Python 3.11+, SQLAlchemy async runtime, PostgreSQL/Neon,
  Redis, Firebase, Gemini, RevenueCat, Sentry.
- Architecture: 4-layer Clean Architecture + CQRS. Domain must not depend on
  external providers.
- Existing request logging: `src/api/middleware/request_logger.py`.
- Existing observability facade: `src/infra/monitoring/observability.py`,
  `connectors.py`, `sentry.py`.
- Existing docs already state Sentry SDK imports belong only in
  `src/infra/monitoring/sentry.py`.
- Pending related plan exists:
  `plans/260613-1308-sentry-logs-metrics-profiles/`.

## Current Log Inventory

Scan command used:

```bash
rg -o "logger\.(debug|info|warning|warn|error|exception|critical|fatal)" src
```

Current explicit logger calls under `src`:

| Level | Count |
| --- | ---: |
| WARNING | 219 |
| INFO | 192 |
| DEBUG | 129 |
| ERROR | 86 |
| EXCEPTION | 7 |
| CRITICAL/FATAL | 0 |

Layer distribution:

| Layer | Count |
| --- | ---: |
| infra | 229 |
| app | 173 |
| domain | 118 |
| api | 103 |
| cron | 10 |

Hotspots by file:

| File | Calls | Main concern |
| --- | ---: | --- |
| `src/infra/adapters/cloudinary_image_store.py` | 28 | URL logging, sync httpx in old path, high debug noise |
| `src/api/routes/v1/webhooks.py` | 27 | RevenueCat identifiers, lifecycle logs, mixed INFO/ERROR |
| `src/infra/adapters/ai_json_utils.py` | 24 | raw AI response snippets |
| `src/app/handlers/query_handlers/lookup_barcode_query_handler.py` | 24 | barcode/provider failures |
| `src/api/main.py` | 24 | startup dependency severity decisions |
| `src/domain/services/meal_suggestion/parallel_recipe_generator.py` | 21 | recipe/provider failure noise |
| `src/infra/services/firebase_service.py` | 14 | push/token/provider errors |
| `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py` | 13 | image URL logging |
| `src/infra/event_bus/pymediator_event_bus.py` | 12 | background handler failure visibility |
| `src/api/dependencies/auth.py` | 11 | auth error severity and noise |

## Key Problems

### 1. WARNING Is Overused

Current middleware promotes every 4xx to WARNING. That conflicts with the target
definition: WARNING should mean unexpected but non-breaking. Expected 400/401/404
responses are often normal API behavior.

Recommendation:

- INFO: expected 2xx/3xx and expected 4xx.
- WARNING: slow request, 429, unexpected 4xx spike, degraded dependency fallback.
- ERROR: unhandled exception or 5xx.
- CRITICAL: readiness/liveness failure for core dependency or startup cannot run.

### 2. CRITICAL Is Missing

No current `logger.critical` or `logger.fatal` use. This means unrecoverable states
are not distinguished from ordinary errors.

Candidate CRITICAL conditions:

- App startup cannot initialize Firebase when auth is required.
- App startup cannot initialize database when DB is required.
- Core health/readiness check determines API cannot serve traffic.
- Event bus/background task manager enters unrecoverable state.
- Out of memory/process termination is usually platform-level, but app can log
  CRITICAL before controlled shutdown when detected.

Avoid CRITICAL for optional services:

- Redis unavailable when cache degradation is allowed.
- PostHog disabled/misconfigured.
- Gemini cache warmup failed but uncached calls continue.
- Email disabled or Resend missing.

### 3. Sensitive Or Noisy Content Appears In Logs

Representative examples:

- Cloudinary URLs logged in `cloudinary_image_store.py`.
- Upload handler logs full `image_url` on success/invalid URL.
- Vision AI logs first 500 chars of model response on parse failure.
- Resend logs recipient email and subject.
- RevenueCat webhook logs app user ID, aliases, product ID, and user ID.

These may be acceptable in local debugging, but not as production logs. They also
conflict with existing Sentry docs that exclude emails, food payloads, raw image
URLs, provider payloads, and secrets.

Recommendation:

- Log stable internal IDs only when needed.
- Redact or hash emails, external URLs, tokens, provider IDs, and raw AI content.
- For AI parse failures, log length, parser stage, error type, and correlation ID,
  not raw content.
- For image URLs, log `image_id`, provider, operation, and status, not URL.
- For webhook identifiers, log internal event ID and type. Keep provider payload
  details in DB/audit tables if needed, not general logs.

### 4. Mixed Formatting Blocks Future Structure

Many call sites use f-strings:

```python
logger.error(f"Failed to send email to {to}: {e}")
```

This eagerly formats strings, weakens structured logging migration, and makes
redaction harder.

Recommendation:

```python
logger.error("Failed to send email: provider=%s error_type=%s", "resend", type(exc).__name__)
```

Use `%s` arguments for logging. Use `exc_info=True` or `logger.exception(...)`
when stack trace is needed.

### 5. Logs, Sentry Events, Metrics, And Audit Events Are Blurred

Use each tool for one job:

| Signal | Purpose | Example |
| --- | --- | --- |
| Log | Human-readable operational timeline | request completed, cron phase failed |
| Sentry issue | Exception/error investigation | unhandled 500, swallowed cron failure |
| Metric | Aggregate trend and alert thresholds | p95 latency, cache failures, retry count |
| Audit/business event | Durable business history | RevenueCat lifecycle, affiliate outbox |

Do not use logs as durable audit storage. Do not use Sentry as product analytics.

## Recommended Severity Rules

### INFO

Use for normal operational milestones:

- App startup/shutdown begin and complete.
- Firebase initialized.
- DB warm succeeded.
- Redis connected/disconnected.
- Event bus initialized/closed.
- Cron run started/completed with counts.
- RevenueCat webhook accepted and processed.
- User command completed when it matters operationally.

Avoid INFO for high-volume per-item internals unless sampled or DEBUG.

### WARNING

Use for unexpected but non-breaking behavior:

- Dependency retry or fallback succeeded.
- Redis unavailable but fallback path returned uncached response.
- Slow request over threshold.
- Slow DB/cache sub-step over threshold.
- Invalid webhook authorization.
- Provider timeout with fallback.
- Validation drop that does not break user flow.

WARNING should invite later investigation, not immediate panic.

### ERROR

Use for user-impacting functional failure:

- Unhandled exception.
- Request returns 5xx.
- DB operation fails and user action cannot complete.
- Provider timeout/failure with no acceptable fallback.
- Email/push/payment/webhook failure that blocks promised behavior.
- Background job phase failed after retries.

Use `logger.exception(...)` inside `except` when stack trace is needed. Prefer
`logger.error(..., exc_info=True)` only when not already in an exception handler.

### CRITICAL

Use for unrecoverable system state:

- Required core dependency prevents app from serving.
- Health/readiness check fails for core dependency in production.
- Process is about to exit due to fatal startup/runtime invariant.
- No worker can process requests or background jobs.

CRITICAL should page. If it would not page, it is probably ERROR or WARNING.

## Layer Conventions

### API Layer

- Request/response logging stays in middleware.
- Route handlers should log only boundary events not already covered by middleware.
- Do not log request bodies, auth headers, Firebase claims, uploaded bytes, or raw URLs.
- Move expected validation/auth failures away from WARNING unless suspicious.

### Application Layer

- Command handlers log use-case milestones and failures.
- Queries should be quieter; log only degradation/fallback/slow path.
- Event handlers log background start/complete/failure with event type and safe IDs.
- Do not import Sentry directly. Use facade only when swallowing exceptions.

### Domain Layer

- Keep logs minimal and provider-neutral.
- DEBUG for calculation internals.
- WARNING only for domain anomalies that are corrected by fallback.
- No external observability imports.
- Avoid user-provided text, food payloads, prompts, raw AI/provider content.

### Infrastructure Layer

- This is where provider/adapter logs belong.
- INFO for connection lifecycle and completed cron batches.
- WARNING for retry/degrade/fallback.
- ERROR for provider failure with no fallback.
- CRITICAL only for required dependency failure that makes the service unusable.

### Cron

- Log run start, phase start, phase complete, final summary.
- Phase failure after retry: ERROR.
- Whole cron cannot run due required DB/config: ERROR or CRITICAL depending on
  whether it affects core production health.
- Always flush observability facade before exit when using captured exceptions.

## Privacy And Cardinality Policy

Never log:

- Request or response bodies.
- Authorization headers.
- Firebase tokens or full claims.
- API keys, service account JSON, secrets.
- FCM tokens.
- Email addresses.
- Food payloads, meal descriptions, raw prompts.
- Raw AI response text.
- Raw image URLs.
- Raw provider webhook payloads.

Allowed attributes:

- `request_id`
- route/path, method, status code
- elapsed milliseconds
- internal user ID when needed
- internal meal/image/event/job ID
- provider name
- operation name
- error type
- attempt count
- coarse result counts

High-cardinality caution:

- User ID is okay in logs for investigation, but not as a metric tag.
- Image ID and event ID are okay in logs, not metric tags.
- Route template is better than raw path for metrics.
- Error type is better than full error message for tags.

## Sentry Strategy

Keep current facade direction:

- `sentry_sdk` imports only in `src/infra/monitoring/sentry.py`.
- Python `ERROR` logs can become Sentry issues through LoggingIntegration.
- INFO/WARNING should not become Sentry issues by default.
- Debug/info logs can be breadcrumbs or Sentry Logs only after privacy filtering.
- Metrics support should land through the pending facade plan, not direct SDK use.

Event contract should remain:

- Send: unhandled 500s, unexpected exceptions, swallowed cron failures, permanent
  outbox failures.
- Do not send: expected 4xx, business exceptions, product analytics, request bodies,
  emails, food payloads, raw URLs, raw provider payloads.

## Approach Options

### Approach A - Documentation Only

Write logging rules and ask developers to follow them.

Pros:

- Fast.
- No runtime risk.

Cons:

- Existing logs stay noisy.
- New code will drift.
- No enforcement.

Verdict: insufficient alone.

### Approach B - Strategy Plus Targeted Cleanup

Document rules, then clean high-risk call sites and add tests/guardrails.

Pros:

- Best balance.
- Reduces privacy risk.
- Aligns with current Sentry facade.
- Does not require logging platform rewrite.

Cons:

- Requires focused implementation pass.
- Some tests need log expectation updates.

Verdict: recommended.

### Approach C - Full Structured Logging Rewrite

Adopt structlog or JSON logging everywhere.

Pros:

- Strong long-term queryability.
- Easier downstream log processing.

Cons:

- Large migration.
- High churn across 600+ call sites.
- Easy to break existing tests and Sentry behavior.
- Overkill before severity/privacy cleanup.

Verdict: later only, if logs are consumed by a dedicated log platform.

## Recommended Design

Use Approach B.

Deliverables for next implementation plan:

1. Add/extend docs with production logging taxonomy.
2. Add `LOG_LEVEL` to settings/env docs, keeping current env behavior.
3. Update request middleware policy:
   - INFO for normal success and expected client errors.
   - WARNING for slow responses and suspicious/non-breaking failures.
   - ERROR for 5xx.
4. Redact high-risk logs:
   - Cloudinary URLs.
   - uploaded image URLs.
   - Resend recipient/subject.
   - raw AI response snippets.
   - RevenueCat aliases/provider identifiers where not needed.
5. Convert high-risk f-string logs to lazy `%s` format.
6. Introduce CRITICAL only for core readiness/startup failure paths.
7. Add focused tests:
   - request middleware severity matrix.
   - no auth/body/email/url/raw AI content in representative logs.
   - Sentry facade remains only SDK import path.
8. Keep broader structured logging migration out of scope.

## Suggested First Cleanup Targets

| Priority | Target | Reason |
| --- | --- | --- |
| P0 | `src/infra/adapters/vision_ai_service.py` | raw AI output snippet in ERROR |
| P0 | `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py` | raw image URL in logs/errors |
| P0 | `src/infra/adapters/resend_email_adapter.py` | email recipient and subject |
| P1 | `src/infra/adapters/cloudinary_image_store.py` | raw URLs and high debug noise |
| P1 | `src/api/middleware/request_logger.py` | all 4xx currently WARNING |
| P1 | `src/api/routes/v1/webhooks.py` | provider IDs and lifecycle severity |
| P2 | f-string logger migration in hotspots | enables safer structure later |
| P2 | docs/tests around CRITICAL | prevents alert misuse |

## Validation Criteria

- `rg "import sentry_sdk|sentry_sdk\\." src` still only matches
  `src/infra/monitoring/sentry.py`.
- `rg "logger\\.(critical|fatal)" src` finds only approved core-failure paths.
- Tests prove expected 4xx responses do not create WARNING logs.
- Tests prove 5xx/unhandled exceptions still create ERROR logs.
- Tests prove representative logs do not include:
  - email addresses
  - raw image URLs
  - auth tokens
  - raw AI response snippets
  - request bodies
- Docs define INFO/WARNING/ERROR/CRITICAL and ownership by layer.

## Risks

- Too much cleanup at once causes churn. Mitigation: start with P0/P1 only.
- Downgrading all 4xx blindly may hide abuse. Mitigation: keep 429 and invalid
  webhook auth as WARNING; add metrics for auth failures later.
- CRITICAL can become alert spam. Mitigation: require "page-worthy" rule.
- Structured logging rewrite is tempting. Mitigation: defer until after taxonomy
  and privacy cleanup.

## Next Steps

1. Approve Approach B.
2. Create `/ck:plan --tdd` from this report.
3. Implement P0/P1 cleanup first.
4. Verify with targeted log tests and existing Sentry facade tests.
5. Update docs after behavior is locked.

## Unresolved Questions

- Should expected 401/403 auth failures be INFO or WARNING in production? My
  recommendation: INFO for ordinary failures, WARNING only for suspicious spikes
  or webhook/admin boundary failures.
- Should internal user ID remain allowed in request logs? My recommendation:
  yes for backend investigation, no as metric tag, never email/Firebase UID.
- Should Sentry Logs be enabled before or after this cleanup? My recommendation:
  after P0 privacy cleanup, before broad metrics work.
