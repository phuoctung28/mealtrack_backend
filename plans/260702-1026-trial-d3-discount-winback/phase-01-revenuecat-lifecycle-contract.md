---
phase: 1
title: "RevenueCat lifecycle contract"
status: completed
priority: P1
effort: "0.5-1d"
dependencies: []
---

# Phase 1: RevenueCat lifecycle contract

## Context Links

- Research: `research/researcher-01-revenuecat-posthog-workflows.md`
- Scout: `research/researcher-02-codebase-scout.md`
- Backend model: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/database/models/subscription.py`
- RevenueCat webhook: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py`
- Settings: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/config/settings.py`

## Overview

Create durable server-side facts for trial period, cancellation intent, and trial-end discount claim. This is the audience source of truth for push and email.

## Key Insights

- `subscriptions` currently caches only `status`, `product_id`, `purchased_at`, `expires_at`, and `cancelled_at`.
- Cancellation sets `status='cancelled'`, but the user still has entitlement until `expires_at`.
- `period_type`, `cancel_reason`, and discount fields arrive on RevenueCat events, but only some are mirrored to PostHog today.
- Do not depend on `offering_id` unless a sandbox webhook proves it exists.

## Requirements

- Functional: persist latest RevenueCat `period_type`, trial start/expiry, cancellation reason, and whether the trial-end discount was claimed.
- Functional: detect claim from configured discounted product IDs and/or RevenueCat discount identifiers.
- Functional: keep RevenueCat as source of truth; backend only caches queryable campaign state.
- Non-functional: no raw webhook payload persistence, no email/PII in logs, migration is Alembic-only.

## Architecture

RevenueCat webhook -> `webhooks.py` handler -> subscription cache columns -> PostHog lifecycle capture -> cron eligibility query.

Minimum schema addition on `subscriptions`:

- `period_type` nullable string, latest RevenueCat period type.
- `trial_started_at` nullable timestamptz.
- `trial_expires_at` nullable timestamptz.
- `cancel_reason` nullable string.
- `trial_end_discount_claimed_at` nullable timestamptz.
- `trial_end_discount_product_id` nullable string.
- `trial_end_discount_identifier` nullable string only if sandbox payload confirms a stable field.

Config:

- `TRIAL_END_DISCOUNT_PRODUCT_IDS`, comma-separated.
- `TRIAL_END_DISCOUNT_IDENTIFIERS`, comma-separated, optional.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/database/models/subscription.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/api/routes/v1/webhooks.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/config/settings.py`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/repositories/subscription_repository_async.py`
- Create: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/migrations/versions/YYYYMMDDHHMMSS_subscription_trial_offer_state.py`
- Modify/Add: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/api/test_webhook_handler.py`
- Modify/Add: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/repositories/test_subscription_repository_async.py`

## Implementation Steps

1. Capture sanitized sandbox webhook samples for `INITIAL_PURCHASE`, `CANCELLATION`, and discounted conversion/purchase. Confirm whether `discount_identifier` exists.
2. Add Alembic migration and ORM columns. Keep nullable to support existing rows.
3. Add settings for discount product IDs and optional discount identifiers.
4. Update `handle_purchase`, `handle_renewal`, and `get_or_create_subscription` to populate `period_type`, trial timestamps, and claim fields.
5. Update `handle_cancellation` to persist `cancel_reason` while keeping `expires_at`.
6. Update `capture_subscription_lifecycle_event` to include `trial_end_discount_claimed`, `trial_expires_at_ms`, and `days_until_expiration` when available.
7. Add unit tests for trial purchase, cancellation during trial, normal conversion, and discounted claim detection.

## Todo List

- [ ] Verify RevenueCat sandbox payload fields for discounted purchase.
- [x] Add migration and ORM columns.
- [x] Add discount claim config.
- [x] Persist trial and claim fields in webhook handlers.
- [x] Extend PostHog lifecycle properties without PII.
- [x] Add webhook and repository tests.

## Success Criteria

- [x] Backend can query "trial user, unexpired, not claimed discount" without relying on mobile local state.
- [x] Cancelled-but-unexpired trial retains `expires_at`, `period_type`, and `cancel_reason`.
- [x] Discount claim is marked only after a RevenueCat-confirmed discounted purchase/conversion.
- [x] Existing RevenueCat webhook tests still pass.

## Risk Assessment

- Risk: RevenueCat payload lacks discount identifier. Mitigation: product ID config is primary, identifier is optional.
- Risk: Existing rows have no `period_type`. Mitigation: fallback to `purchased_at` within 7 days only during rollout.
- Risk: `webhooks.py` is already large. Mitigation: extract small pure helpers if new logic would grow the file further.

## Security Considerations

- Do not store raw webhook JSON.
- Do not log RevenueCat aliases, emails, raw product payloads, or auth headers.
- Keep webhook secret verification unchanged.

## Next Steps

Phase 2 uses these fields to build the push eligibility query.
