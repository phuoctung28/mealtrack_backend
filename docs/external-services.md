# Backend External Services Integration

**Last Updated:** June 18, 2026
**Services:** Firebase, Cloudinary, Google Gemini, RevenueCat, PostHog, Redis, Sentry, DeepL, FatSecret, OpenFoodFacts, Brave Search, Pexels, Unsplash, Resend, Cloudflare Workers AI, Google Imagen, Pollinations, nutree-affiliate
**Failure handling:** Optional integrations degrade when safe. Firebase Auth and the primary DB fail fast. Redis optional caches degrade by bypassing cache; any Redis-backed required state must be documented and health-checked separately.

---

## Firebase

**Purpose:** Authentication + Push Notifications (FCM)

### Authentication
- Firebase Admin SDK for JWT verification
- Dev bypass middleware enabled by `DEV_MODE=true` (`X-Dev-User-Id` header)
- Maps Firebase UID to database UUID

**Config:** `FIREBASE_CREDENTIALS=path/to/credentials.json`

### Firebase Cloud Messaging (FCM)
- Platform-specific payload builders in `src/infra/services/push/`
  - `android_payload_builder.py`: high-priority Android config with channel ID (`meal_reminders` or `daily_summary`)
  - `apns_payload_builder.py`: APNs Time Sensitive payload with `interruption-level` in payload body (not headers), priority 10
- `FirebaseService` rejects blank title/body before building APNs payloads and mobile `data` fields
- Multi-device support via `user_fcm_tokens` table
- Deduplication across workers via `notification_sent_log` table (migration 047)
- Trial-expiry pushes at T-2d and T-1d via `CronTrialPushService` (`src/infra/services/cron_trial_push_service.py`)
- Notifications rescheduled automatically on timezone changes — triggered from `UpdateTimezoneCommandHandler` and `RegisterFcmTokenCommandHandler`
- Cron push entrypoint (`src/cron/push.py`) owns all push scheduling: precompute notification rows, schedule trial-expiry rows, claim due rows, batch-send, mark sent, clean expired rows
- Cron dispatch helper (`CronNotificationDispatchService`) uses database row claiming (`pending` → `processing`) plus stale-processing recovery instead of a background loop or leader lock
- APNs diagnostics surfaced at `/health/notifications` via `apns_diagnostics()` to verify `interruption-level` placement

---

## Cloudinary

**Purpose:** Image Storage + CDN

- Folder organization ("mealtrack"), secure URL generation
- Format support: JPEG, PNG
- Fallback to direct URL construction if Resource API unavailable

**Config:** `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

**Used for:** Meal images, user avatars

---

## Google Gemini

**Purpose:** AI Meal Analysis + Content Generation (primary AI provider)

### Multi-Model Strategy (Rate Distribution)

| Purpose | Model | Env Key |
|---------|-------|---------|
| General / Recipe / Barcode | `gemini-2.5-flash` | `GEMINI_MODEL` |
| Meal names | `gemini-2.5-flash-lite` | `GEMINI_MODEL_NAMES` |
| Recipe generation | `gemini-2.5-flash-lite` | `GEMINI_MODEL_RECIPE` |

### Provider Fallback Architecture

`AIModelManager` orchestrates providers through `AIProviderPort`. Each purpose has a fallback chain; models are tried in order until one succeeds. The circuit breaker opens after 5 failures within 60s and allows retry after 30s.

**Default text chain (e.g. RECIPE):**
```
gemini-2.5-flash-lite  →  gemini-2.5-flash  →  @cf/google/gemma-4-26b-a4b-it  (if CF enabled)
```

**Vision / parse chains (always Gemini-only in v1):**
```
gemini-2.5-flash-lite  →  gemini-2.5-flash
```

Logs emitted: `[AI-ATTEMPT]`, `[AI-FALLBACK-SUCCESS]`, `[AI-ATTEMPT-FAILED]`. Never log prompt content, food payloads, or raw AI output.

### Vision AI (Meal Analysis)
- 6 analysis strategies: basic, portion-aware, ingredient-aware, weight-aware, user-context, combined
- JSON parsing with multiple fallbacks: direct, markdown extraction, regex, truncation recovery
- Safety detection for blocked responses

### Token Limits by Use Case

| Use Case | Tokens |
|----------|--------|
| Weekly meal plan | 8000 |
| Meal suggestions (per count, max 8000) | 1500 × count |
| Daily multi-meal | 3000 |
| Single meal | 1500 |

**Config:** `GOOGLE_API_KEY`

---

## Cloudflare Workers AI (Text Fallback)

**Purpose:** Optional fallback AI provider for text-only purposes when Gemini is degraded. Disabled by default.

**Not supported in v1:** vision/image analysis. `MEAL_SCAN` and `INGREDIENT_SCAN` remain Gemini-only. Parse and barcode require explicit opt-in via `CLOUDFLARE_WORKERS_AI_TEXT_PURPOSES`.

### How It Works

- Uses LangChain's `ChatCloudflareWorkersAI` (`langchain-cloudflare>=0.3.4`) — this is LangChain inside FastAPI, not the app running on Cloudflare Workers runtime.
- Cloudflare model IDs stored raw (`@cf/...`) in fallback chains; `AIModelManager` routes to the CF provider via an explicit ownership map.
- If `CLOUDFLARE_AI_GATEWAY_ID` is set, LangChain passes it as the `ai_gateway` field to Workers AI.
- Returns the same `dict` shape as `GeminiProvider` — handlers are provider-agnostic.
- Circuit breaker trips on 429/5xx/timeout, same as Gemini.

### Env Vars

| Key | Default | Description |
|-----|---------|-------------|
| `CLOUDFLARE_WORKERS_AI_ENABLED` | `false` | Master switch — Workers AI is inactive unless this is `true` |
| `CLOUDFLARE_ACCOUNT_ID` | `` | Cloudflare account ID |
| `CLOUDFLARE_API_TOKEN` | `` | API token with Workers AI permission |
| `CLOUDFLARE_AI_GATEWAY_ID` | `` | Optional AI Gateway ID; leave blank for direct Workers AI |
| `CLOUDFLARE_WORKERS_AI_TEXT_MODEL` | `@cf/google/gemma-4-26b-a4b-it` | Model for text generation |
| `CLOUDFLARE_WORKERS_AI_TEXT_PURPOSES` | `recipe,general,meal_names,discovery` | Purposes that include CF in fallback chain |
| `CLOUDFLARE_WORKERS_AI_JSON_MODE` | `true` | Reserved; currently unused by LangChain adapter |
| `CLOUDFLARE_WORKERS_AI_TIMEOUT_SECONDS` | `30` | HTTP timeout per request |

### Production Rollout Order

```
1. Deploy code — Cloudflare disabled by default; zero behavior change.
2. In Render: set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN.
3. Leave CLOUDFLARE_AI_GATEWAY_ID blank for direct Workers AI.
4. Set CLOUDFLARE_WORKERS_AI_ENABLED=true, TEXT_PURPOSES=recipe,general.
5. Observe app logs and Cloudflare Workers AI usage for several days.
6. Extend TEXT_PURPOSES to include meal_names,discovery after basic observation passes.
7. Keep parse_text, barcode, meal_scan, ingredient_scan Gemini-only until separate schema eval.
```

### Rollback

```
CLOUDFLARE_WORKERS_AI_ENABLED=false
```

### Privacy Notes

- API token is loaded from env/settings and never logged.
- Logs include only: provider name, model alias, purpose value, HTTP status code, and error class.
- Prompts, food payloads, raw AI responses, and account IDs are never logged.

---

## RevenueCat

**Purpose:** Subscription Management

- Webhook sync to local `subscriptions` table
- Premium status check with Redis cache fallback
- Signature verification via constant-time HMAC comparison
- Webhook events handled in `src/api/routes/v1/webhooks.py`:

| Event | Action |
|-------|--------|
| `INITIAL_PURCHASE` | Create subscription record, credit referral wallet |
| `RENEWAL` | Update expiry, reset billing-issue flag |
| `CANCELLATION` | Set status to `cancelled` |
| `EXPIRATION` | Set status to `expired` |
| `BILLING_ISSUE` | Set status to `billing_issue` |
| `PRODUCT_CHANGE` | Update product ID and expiry |
| `REFUND` | Set status to `refunded`, revoke referral credit |
| `TRANSFER` | Re-point subscription to new subscriber ID |

- PostHog lifecycle mirroring for CANCELLATION, EXPIRATION, BILLING_ISSUE, REFUND, RENEWAL, PRODUCT_CHANGE events (configurable via `POSTHOG_API_KEY`)

**Config:** `REVENUECAT_SECRET_API_KEY`, `REVENUECAT_WEBHOOK_SECRET`

**Status:** Premium feature gates planned, not currently enforced on routes

---

## PostHog

**Purpose:** Product analytics — subscription lifecycle event capture

- `src/infra/adapters/posthog_adapter.py`: fire-and-forget async capture via `httpx` (3s timeout)
- Only sends events when `POSTHOG_API_KEY` is set; silently skips otherwise
- Currently captures subscription lifecycle events mirrored from RevenueCat webhooks

**Config:** `POSTHOG_API_KEY`, `POSTHOG_HOST` (default: `https://app.posthog.com`)

---

## Redis Cache

**Purpose:** Selective performance and AI-cost optimization. Redis is not the source of truth for user nutrition, notification delivery, FCM token ownership, or write-path correctness.

- **Default posture:** Do not cache unless the value passes the cache admission checklist in `docs/superpowers/specs/2026-05-21-redis-optimize-design.md`.
- **Pattern:** Cache-aside only for optional read caches where DB/API fallback is correct.
- **Connection Pool:** 10 connections by default (`REDIS_MAX_CONNECTIONS`) | **Default TTL:** 1 hour
- **Error Handling:** Optional caches degrade by bypassing Redis. Required Redis-backed state must be documented and health-checked separately.

**Config:** `REDIS_URL=redis://host:port/db`

### Cache Policy by Data Type

| Data | Redis Policy |
|------|--------------|
| Food search/details | Cache; stable-ish data with high reuse |
| Nutrition lookup | Cache; expensive lookup chain with bounded stale window |
| Gemini explicit cache names | Cache; cost optimization only, fall back to uncached calls |
| Daily/weekly nutrition read models | Conditional cache; short TTL plus write/event invalidation |
| Auth UID mapping | Process-local TTL cache, not Redis |
| Notification precompute and FCM token ownership | Do not cache; database is source of truth |
| Meal suggestion sessions | Not cache; transient state. Prefer Postgres with `expires_at`, or treat Redis as required state store if kept |

---

## Sentry Monitoring

**Purpose:** Error tracking, Sentry Logs, operational metrics, performance profiling, crash reporting

- Sentry is an infrastructure connector only. Runtime code calls `src.infra.monitoring` facade functions; direct `sentry_sdk` imports belong only in `src/infra/monitoring/sentry.py`.
- FastAPI, Starlette, SQLAlchemy, and logging integrations are initialized before the `FastAPI` app is created.
- Sentry Logs are emitted only through the provider-neutral `log_event(...)` facade when `SENTRY_ENABLE_LOGS=true`.
- Operational metrics are emitted only through provider-neutral metric facade calls when `SENTRY_ENABLE_METRICS=true`.
- Gracefully disabled if `SENTRY_DSN` is not set; the facade falls back to no-op behavior.
- Request context is allowlisted: request ID, method, route/path, environment, release, and internal user ID when available.
- Log and metric attributes use the same allowlist and scalar-only filtering as request context.
- Cron entrypoints capture swallowed failures and flush via the facade before exit.
- Affiliate outbox permanent failures send an operational alert with row/event identifiers only; raw affiliate payload is never attached.

**Config:** `SENTRY_DSN`, `SENTRY_RELEASE`, `SENTRY_ENABLE_LOGS=true`, `SENTRY_ENABLE_METRICS=true`, `SENTRY_TRACES_SAMPLE_RATE=0.1`, `SENTRY_PROFILES_SAMPLE_RATE=0.05`, `SENTRY_PROFILE_SESSION_SAMPLE_RATE`, `SENTRY_PROFILE_LIFECYCLE`, `SENTRY_SEND_PII=false`

### Single-Owner Rule and Duplicate Suppression

Python `ERROR` log records are automatically captured by Sentry as issues via the logging integration. This means every `logger.error(...)` in the request path generates a Sentry issue — logging the same failure twice (log-and-rethrow pattern) produces two distinct Sentry issues for one real event.

The single-owner logging strategy prevents this:
- **One root-cause ERROR per unexpected request failure** — owned by `src/api/exception_handlers.py`.
- **Expected 4xx domain exceptions** convert silently to responses; zero ERROR logs and zero Sentry issues.
- **Background/cron boundaries** own their own ERROR log + `capture_exception` because they swallow rather than propagate.

When to call each facade function:

| Function | When |
|----------|------|
| `capture_exception(exc)` | Swallowed exceptions at background/cron boundaries that never reach the global handler |
| `log_event("warning", "...")` | Degradation signals that need structured log metadata (e.g. `ai.provider.failure`) |
| `increment_metric("...")` | Operational counters: permanent outbox failures, retry counts |
| `distribution_metric("...")` | Latency histograms: `meal.manual_save.db_ms`, `meal.manual_save.cache_ms` |

Do **not** call `capture_exception` after a `logger.error(..., exc_info=True)` — the logging integration already ships it to Sentry.

### Event Contract

Sent to Sentry:
- Unhandled API exceptions and unexpected 500-class failures.
- `ERROR` logs with exception info through the logging integration.
- Structured operational logs emitted through the facade when Sentry Logs are enabled.
- Operational counter, gauge, and distribution metrics emitted through the facade.
- Caught-and-swallowed cron failures.
- Affiliate outbox permanent failures.
- Sampled FastAPI/Starlette request transactions, SQLAlchemy spans, coarse cron spans, and sampled profiles.

Not sent to Sentry:
- Expected 4xx validation/auth/not-found responses or business exceptions.
- Product analytics or audit logs.
- Request/response bodies, auth headers, Firebase tokens/claims, emails, food payloads, raw image URLs, raw provider payloads, or secrets.
- Debug/info Python logging records as Sentry issues.
- Unstructured application logs outside the observability facade.

### Application Log Severity

Use the production log levels as an operational contract:

- `INFO`: normal milestones, successful startup/cron/request completion, and
  expected client rejections such as 400/401/403/404.
- `WARNING`: unexpected but non-breaking signals such as slow requests, 429 rate
  limits, invalid webhook authorization, automatic retries, and optional
  dependency degradation.
- `ERROR`: user-impacting failures that need engineering attention, including
  unhandled exceptions, 5xx responses, and broken required provider calls.
- `CRITICAL`: page-worthy service-unusable paths only, such as a required
  startup dependency failure that aborts serving.

Log content must remain safe before it reaches Sentry or any downstream log
sink. Do not log emails, email subjects, auth data, Firebase claims, raw image
URLs, raw AI response text, food payloads, raw webhook provider payloads, DSNs,
API keys, or service account JSON. Use operation names, generated internal IDs,
event types, environment, durations, sizes, counts, and error class names.

### Operational Setup

- Alerts: page on new/reopened production issues with level `error`; route affiliate outbox permanent failures to backend operations.
- Dashboards: track error rate, p95 request latency, slow SQL spans, cron failure count, and affiliate outbox permanent failure count.
- Release health: set `SENTRY_RELEASE` during deploy so issues and performance regressions are grouped by release.

---

## Database (PostgreSQL/Neon)

See `database-guide.md` for schema, connection pool, and migration details.

**Config:** `APP_DATABASE_URL=postgresql://user:pass@host/db` for app runtime; `DATABASE_URL_DIRECT` is migration/admin only.

---

## Service Health Checks

```
GET /health                    # Basic health (200 if running)
GET /v1/health/db-pool         # DB pool metrics
GET /v1/health/db-connections  # PostgreSQL connection stats
GET /v1/health/notifications   # FCM health
```

---

## Error Handling & Graceful Degradation

| Service | Failure Mode | Recovery |
|---------|--------------|----------|
| Firebase Auth | Fail fast (401) | Requests rejected |
| PostgreSQL | Fail fast (503) | Requests rejected |
| Gemini | Circuit breaker → try fallback | Falls through to next model in chain |
| Workers AI | Circuit breaker (429/5xx/timeout) | Trips same circuit breaker; chain exhausted → AIUnavailableError |
| Cloudinary | Degrade (fallback URL) | Continue with best-effort image |
| RevenueCat | Degrade (assume premium from cache) | Continue with last-known status |
| PostHog | Degrade (log warning) | Continue without analytics |
| Redis | Degrade (bypass cache) | Continue without caching |
| Sentry | Degrade (log locally) | Continue with local logging |

---

---

## nutree-affiliate (Internal Service)

**Purpose:** Affiliate identity, code management, commission ledger, and payout state for KOL/PT partner program. Runs as a separate Vercel deployment with its own Neon Postgres database.

**Ownership boundary:** MealTrack must never join against or write the affiliate database directly. All affiliate state lives in nutree-affiliate.

### Integration Points

| Direction | Protocol | Endpoint |
|-----------|----------|----------|
| MealTrack → nutree-affiliate | HMAC-signed HTTP POST | `POST /api/internal/codes/validate` |
| MealTrack → nutree-affiliate | HMAC-signed HTTP POST | `POST /api/internal/mealtrack-events` |

### Request Signing (HMAC-SHA256)

```
message  = f"{unix_timestamp}.{raw_body}"
signature = HMAC-SHA256(AFFILIATE_INTERNAL_SECRET, message)
headers   = { X-Timestamp: unix_timestamp, X-Signature: hex_signature }
```

Replay window: ±300 seconds. Implemented in `src/infra/adapters/affiliate_service_adapter.py`. Cross-service contract test in `tests/unit/infra/adapters/test_affiliate_service_adapter_signing.py`.

### Lifecycle Event Flow

RevenueCat webhook → MealTrack webhook handler → `affiliate_event_outbox` (same DB transaction) → cron dispatcher → nutree-affiliate `/api/internal/mealtrack-events`.

Events enqueued: `subscription_initial_purchase`, `subscription_renewal`, `subscription_canceled`, `subscription_expired`, `subscription_refund`.

Events do **not** include `affiliate_id` — nutree-affiliate resolves it internally by `mealtrack_user_id`. Events for non-attributed users are silently ignored by nutree-affiliate.

### Outbox Table (`affiliate_event_outbox`)

| Column | Notes |
|--------|-------|
| `event_id` | Idempotency key forwarded to nutree-affiliate inbox |
| `status` | `pending` / `sent` / `failed` |
| `attempts` | Max 5; exponential back-off 1m→5m→30m→2h |
| `next_attempt_at` | Dispatcher claims rows where `status=pending AND next_attempt_at <= now` |

Permanent failures (5 attempts exhausted) capture a Sentry error. Cron: `src/cron/affiliate_outbox.py` — schedule every 5 min.

### Failure Modes

| Failure | MealTrack behavior |
|---------|--------------------|
| nutree-affiliate down during code validate | Returns `active=False`; apply raises `invalid_code` |
| nutree-affiliate down during attribution | Logs warning; apply still succeeds; no retry |
| nutree-affiliate down during lifecycle event | Outbox row stays `pending`; retried on next cron run |
| Outbox row hits max retries | Status → `failed`, Sentry alert fired |

**Config:** `AFFILIATE_INTEGRATION_ENABLED`, `AFFILIATE_API_BASE_URL`, `AFFILIATE_INTERNAL_SECRET`, `AFFILIATE_CODE_VALIDATE_TIMEOUT_SECONDS` (default 3.0s)

### Rollout Checklist

1. Create nutree-affiliate Neon database and run `npx ts-node api/migrate.ts`
2. Set `AFFILIATE_INTERNAL_SECRET` in both nutree-affiliate and MealTrack (same value)
3. Set `AFFILIATE_API_BASE_URL` in MealTrack (e.g. `https://nutree-affiliate.vercel.app`)
4. Deploy nutree-affiliate **before** enabling MealTrack feature flag
5. Set `AFFILIATE_INTEGRATION_ENABLED=true` in MealTrack
6. Add Render cron job: `python -m src.cron.affiliate_outbox` — every 5 min
7. Monitor `affiliate_event_outbox` for `status=failed` rows and Sentry alerts
8. Rotate `AFFILIATE_INTERNAL_SECRET` if compromised — update both services simultaneously

---

See related: `system-architecture.md`, `database-guide.md`, `cqrs-guide.md`
