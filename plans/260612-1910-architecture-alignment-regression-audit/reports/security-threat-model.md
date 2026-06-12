---
title: "Repository security threat model"
date: "2026-06-12"
scope: "MealTrack backend"
source: "Codex Security threat-model guidance"
---

# Repository Security Threat Model

## Overview

MealTrack backend is a FastAPI service for meal tracking, nutrition analysis,
notifications, subscriptions, referrals, movement, hydration, and AI-assisted
meal generation. It stores private user health/nutrition data and coordinates
with Firebase, RevenueCat, Cloudinary, Redis, Neon Postgres, Gemini, and
nutree-affiliate.

Primary runtime surfaces:

- Authenticated mobile/API endpoints under `src/api/routes/v1`.
- Firebase JWT auth and development auth bypass middleware.
- RevenueCat webhooks for subscription lifecycle events.
- Affiliate validation/apply/outbox dispatch.
- Cloudinary image upload, direct-upload signatures, and image URL scan paths.
- Redis optional cache and required transient meal suggestion sessions.
- Cron/service paths for notifications, email, affiliate outbox, and trial push.

## Threat Model, Trust Boundaries, And Assumptions

### Assets

- User identity mappings: Firebase UID, MealTrack user ID, email.
- Nutrition, meal, movement, hydration, weight, profile, and weekly budget data.
- Subscription and entitlement state synced from RevenueCat.
- Referral and payout workflow state.
- FCM tokens and notification preferences.
- Cloudinary image IDs, URLs, and upload signatures.
- Affiliate outbox messages and signed internal affiliate requests.
- External service secrets, Firebase credentials, DB URLs, Redis credentials, and
  webhook/HMAC secrets.

### Trust Boundaries

| Boundary | Control |
|---|---|
| Client to API | Firebase JWT auth dependencies and per-user ownership checks |
| Dev auth bypass | Environment-gated middleware, not production behavior |
| Admin operations | Existing `require_admin` pattern when a touched route is already operator-only |
| Subscription state | RevenueCat-backed subscription status is the source of truth |
| RevenueCat to backend | Webhook secret validation before subscription mutation |
| MealTrack to affiliate | HMAC-signed internal API requests and outbox ownership |
| Client image/URL input | Storage-prefix and ownership validation before fetch/mutation |
| Redis cache/state | Selective cache policy; required state must be explicit |
| Migrations/admin scripts | Separate migration DB URL and sync engine path |

### Attacker-Controlled Inputs

- HTTP request bodies, query params, headers, uploaded files, image URLs, and
  dates/timezones/language codes.
- Firebase-authenticated user identity, within what Firebase validates.
- Webhook payloads unless the RevenueCat secret check succeeds.
- Affiliate callback/request payloads unless HMAC verification succeeds.
- Image IDs or URLs supplied by the client.

### Operator-Controlled Inputs

- DB connection mode and pool sizing env vars.
- Redis enablement, connection URL, and fail-on-cache behavior.
- CORS origins, admin emails, monitoring token, webhook secrets, and provider
  API keys.
- Uvicorn worker count and deployment topology.

### Developer-Controlled Inputs

- Alembic migrations and model registry changes.
- Import-linter baselines and architecture test allowlists.
- Cache key families, TTLs, and invalidation paths.
- Prompt templates and AI model/provider routing.

## Attack Surface, Mitigations, And Attacker Stories

### User Ownership And Authorization

Realistic attacker story: an authenticated user attempts to read, edit, or delete
another user's meals, movement logs, hydration entries, saved suggestions,
profile, notification preferences, or payout/referral state.

Mitigation expectation: handlers/repositories must filter by `user_id`, not only
resource ID. Route auth must bind the authenticated user to the command/query.

### RevenueCat Subscription Boundary

Realistic attacker story: an external actor sends forged RevenueCat lifecycle
events or tampers with subscription identifiers to mutate subscription state.

Mitigation expectation: RevenueCat webhook inputs verify the configured secret
before mutation. This plan does not add a broad premium/admin enforcement
rollout.

### Webhook And Internal Service Forgery

Realistic attacker story: an external actor sends forged affiliate callbacks or
internal-event requests to mutate commission state.

Mitigation expectation: affiliate integration remains service-to-service and
HMAC-signed; MealTrack does not join or directly write affiliate DB tables.

### File, URL, And SSRF-Like Inputs

Realistic attacker story: a client submits an arbitrary URL or forged Cloudinary
ID to make the backend fetch unexpected content or mutate another user's image.

Mitigation expectation: scope image IDs/URLs to expected storage prefixes and
ownership before server-side fetch or write. Avoid logging raw image URLs when
they may contain sensitive tokens.

### Cache And Transient State

Realistic attacker story: stale cache returns wrong nutrition or entitlement-like
data after a mutation, or Redis outage breaks a path assumed to be optional.

Mitigation expectation: optional cache must bypass on failure; required transient
state must be documented as required or moved to durable Postgres with
`expires_at`. Write paths persist first, then invalidate derived reads.

### Async Runtime And Availability

Realistic attacker story: expensive AI/image/search requests or blocking sync
HTTP calls under async handlers exhaust workers and cause availability issues.

Mitigation expectation: external I/O is async or behind `to_thread`, long-lived
background work is owned, and rate limits are tuned on expensive endpoints.

### Secrets And Logs

Realistic attacker story: logs expose tokens, service-account JSON, raw payout
details, webhook secrets, or raw food/image payloads.

Mitigation expectation: structured logs include IDs/timing/status only. Secrets
stay in env vars and are never committed.

## Severity Calibration

### Critical

- Cross-user write/read that exposes private health/nutrition/profile data at
  scale.
- Forged webhook or affiliate request that grants subscription/commission/payout
  state without verification.
- Secret leakage for Firebase service accounts, DB URLs, Redis credentials, or
  provider API keys.

### High

- Forged RevenueCat or affiliate event accepted without signature validation.
- Image URL/ID handling that allows arbitrary server-side fetch or another
  user's image mutation.
- Redis required-state outage treated as optional and causing incorrect
  workflow state.
- Blocking external calls in hot async request paths causing worker exhaustion.

### Medium

- Stale computed read cache after meal, hydration, movement, or metric writes.
- Excessive Redis invalidation latency causing write endpoints to become slow.
- Import-boundary drift that makes ownership/security checks harder to reason
  about.
- Missing rate-limit tuning on expensive AI or meal suggestion endpoints.

### Low

- Documentation drift that points to old pool sizing or old task-manager paths.
- Developer-only test fixture sync behavior that does not reach runtime.
- Optional Gemini explicit cache failures that fall back to uncached calls.

## Reuse Notes

Use this threat model for future feature plans and security reviews. It is not a
full vulnerability scan; it identifies the boundaries and attacker stories that
should guide later implementation and testing.
