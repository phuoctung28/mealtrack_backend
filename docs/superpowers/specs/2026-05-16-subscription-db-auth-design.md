# Subscription DB-as-Auth-Source-of-Truth Design

**Date:** 2026-05-16  
**Status:** Approved  
**Branch:** delivery

## Overview

Move subscription authorization off RevenueCat's live API and onto the local PostgreSQL database. RevenueCat continues to handle App Store / Play Store billing and sends webhooks that keep the DB in sync, but no live RC API call is made during request authorization.

## Goals

- DB is the sole source of truth for whether a user has an active subscription
- No RC API calls during the authorization hot path
- Grace period buffer tolerates webhook delivery delays and billing retry windows
- Almost all feature routes gated behind subscription check

## Non-Goals

- Removing RC webhooks (they remain the sync mechanism)
- Removing the `RevenueCatAdapter` class (still used for webhook verification)
- Building any custom billing or receipt validation

---

## Architecture

### Authorization Flow

```
Request
  → Firebase JWT auth middleware
  → User loaded from DB (subscriptions eagerly loaded)
  → require_subscription Depends
      → DB check only (user.get_active_subscription())
      → Pass or HTTP 402
  → Route handler
```

No additional DB query is needed — subscriptions are already on the user object from the auth step.

### Middleware Change (`src/api/middleware/premium_check.py`)

Remove the RevenueCat API fallback. The check becomes pure DB logic:

| Condition | Result |
|-----------|--------|
| No subscription row | 402 immediately |
| `status=active`, `expires_at=None` | Allow (lifetime) |
| `status=active`, `expires_at` in future | Allow |
| `status=active`, `expires_at` in past, within grace period | Allow (webhook delay buffer) |
| `status=cancelled`, `expires_at` in future | Allow (paid through end of period) |
| `status=cancelled`, `expires_at` in past | 402 immediately (no grace period — intentional cancellation) |
| `status=billing_issue`, `expires_at` in future or within grace period | Allow (billing retry window) |
| `status=billing_issue`, past grace period | 402 |
| `status=expired` or `status=refunded` | 402 immediately |

**Grace period:** Configurable via `SUBSCRIPTION_GRACE_PERIOD_HOURS` env var (default: `24`). Added to `Settings`.

**Error response** (unchanged):
```json
{"message": "Standard subscription required", "error_code": "SUBSCRIPTION_REQUIRED"}
```

---

## Route Gating

Applied at router registration level via `dependencies=[Depends(require_subscription)]`. Not per-endpoint.

### Gated Routers (premium features)

- `meals` — meal logging, meal history
- `nutrition` — nutrition analysis, daily/weekly summaries
- `meal_suggestions` — AI meal suggestions
- `saved_suggestions` — saved meal suggestions
- `tdee` — TDEE calculations, calorie targets
- `foods` — food database search
- `ingredients` — ingredient lookup
- `activities` — activity tracking
- `weight_entries` — weight tracking
- `cheat_days` — cheat day tracking
- `user_profiles` — user profile management
- `notifications` — push notification management

### Public Routers (no subscription check)

- `webhooks` — must be reachable without auth for RC to deliver events
- `users` — `/sync` and `/firebase/{uid}` needed for onboarding/login flow
- `promo_codes` — validate/redeem during purchase flow (pre-subscription)
- `referrals` — referral code lookup (pre-purchase)
- `health` — health check endpoint
- `monitoring` — internal metrics/monitoring
- `feature_flags` — feature flag reads (needed before subscription check)
- `docs`, `openapi` — API documentation

---

## Configuration

New env var:

```
SUBSCRIPTION_GRACE_PERIOD_HOURS=24   # hours past expires_at before denying access
```

Added to `Settings` in `src/infra/config/settings.py` and `.env.example`.

---

## What Does NOT Change

- **RC webhooks:** `webhooks.py` is not modified. It already correctly writes `status` and `expires_at` on every lifecycle event (`INITIAL_PURCHASE`, `RENEWAL`, `CANCELLATION`, `EXPIRATION`, `BILLING_ISSUE`, `PRODUCT_CHANGE`, `REFUND`).
- **RevenueCatAdapter:** Stays in the codebase. Used by the webhook handler. No longer imported by `premium_check.py`.
- **`get_subscription_status()`:** The non-raising variant stays available for endpoints that return subscription info without blocking access.
- **DB schema:** No migration needed. The `subscriptions` table already has all required columns (`status`, `expires_at`, `cancelled_at`).

---

## Testing

### Unit tests — `tests/unit/middleware/test_premium_check.py`

| Scenario | Expected |
|----------|----------|
| Active subscription | Pass |
| Cancelled, still within paid period | Pass |
| Billing issue, within grace period | Pass |
| Expired, within grace period | Pass |
| Expired, past grace period | 402 |
| Refunded | 402 |
| No subscription record | 402 |
| Lifetime (expires_at=None) | Pass |

### Integration tests — `tests/integration/test_subscription_gating.py`

- Gated route + valid subscription → 200
- Gated route + no subscription → 402
- Public routes (webhooks, user sync) → reachable without subscription
- Grace period boundary: `expires_at = now - 23h` → pass; `now - 25h` → 402

RC API is not mocked in any test — it is not in the authorization path.

---

## Implementation Sequence

1. Add `SUBSCRIPTION_GRACE_PERIOD_HOURS` to `Settings` and `.env.example`
2. Rewrite `require_subscription` in `premium_check.py` — DB-only, grace period logic
3. Apply `dependencies=[Depends(require_subscription)]` to each gated router in `main.py`
4. Write unit tests for `require_subscription`
5. Write integration tests for gated vs public routes
