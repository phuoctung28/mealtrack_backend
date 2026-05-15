# Email Marketing Promo Codes — Design Spec

**Date:** 2026-05-15
**Branch:** delivery
**Status:** Approved

---

## Overview

A system-generated promo code feature for email marketing campaigns. Users receive a code via email and redeem it in the app (manually at the paywall or via a deep link) to purchase an annual subscription at a discounted price through a dedicated RevenueCat `email` offering.

This is distinct from the existing referral code system: promo codes have no referrer, are created by developers/scripts, and use the `email` RC offering (not the shared `discount` offering used by referral and spin wheel).

---

## Scope

- Backend: new DB tables, validate + redeem API endpoints, Alembic migration
- Mobile: new provider, new paywall UI widget, deep link handling, purchase flow integration
- Out of scope: admin panel UI, monthly plan discounts, per-user unique codes, webhook backfill of `subscription_id` (tracked but deferred to v2)

---

## Data Model

### `promo_codes` table

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | BaseMixin |
| `code` | String(50), unique, indexed | e.g. `SUMMER50` — uppercase recommended |
| `max_uses` | Integer | redemption cap |
| `current_uses` | Integer, default 0 | incremented atomically at redeem time |
| `is_active` | Boolean, default True | soft disable without deletion |
| `expires_at` | DateTime(tz), nullable | optional campaign expiry |
| `description` | String(255), nullable | internal note e.g. "May email blast" |
| `rc_offering_id` | String(50), default `'email'` | which RC offering to purchase from |
| `created_at` | DateTime(tz) | |

Codes are created via direct DB insert or a developer script. No admin UI in v1.

### `promo_code_redemptions` table

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | PrimaryEntityMixin |
| `promo_code_id` | FK → `promo_codes.id` | |
| `user_id` | FK → `users.id` | |
| `redeemed_at` | DateTime(tz) | |
| `subscription_id` | FK → `subscriptions.id`, nullable | backfilled post-webhook in v2 |
| UNIQUE | `(promo_code_id, user_id)` | one redemption per user per code |

---

## API Endpoints

All endpoints require authentication. Prefix: `/v1/promo-codes`.

### `POST /v1/promo-codes/validate`

Called when user inputs or deep-links a code, before purchase. Does NOT increment `current_uses`.

**Request:**
```json
{ "code": "SUMMER50" }
```

**Response (200):**
```json
{
  "code": "SUMMER50",
  "rc_offering_id": "email",
  "is_valid": true
}
```

**Error responses:**
| Status | Condition |
|---|---|
| 404 | Code not found |
| 422 | `is_active = False` or expired |
| 422 | `current_uses >= max_uses` |
| 422 | User has already redeemed this code |

### `POST /v1/promo-codes/redeem`

Called by mobile immediately after a successful RC purchase. Increments `current_uses` atomically and creates the redemption record.

**Request:**
```json
{ "code": "SUMMER50" }
```

**Response (200):**
```json
{ "success": true }
```

**Error responses:** Same validation as validate endpoint. If redeem fails after a successful purchase (race condition, network error), mobile retries silently — the user already has access via RC, so the redemption record is the only thing at risk.

---

## Mobile Architecture

### New Providers

**`pendingPromoCodeProvider`** — `StateNotifierProvider`, keepAlive.

Mirrors `pendingReferralCodeProvider`. Holds a `PendingPromoCode(code, rcOfferingId)` after successful validation, or null. Exposes:
- `validate(code)` — calls `POST /v1/promo-codes/validate`, stores result on success
- `redeem(code)` — calls `POST /v1/promo-codes/redeem`, clears state on success

**`promoOfferingProvider`** — `FutureProvider`.

Calls `offerings.getOffering('email')`. Returns the annual package from the `email` RC offering. Mirrors `referralOfferingProvider`.

### Paywall UI — `PromoCodeInput` Widget

Added to `PaywallContent` alongside the existing `ReferralCodeInput`.

- Same collapsible pattern: collapsed link ("Have a promo code?") → expanded input → applied green banner
- Code input: alphanumeric + hyphens, uppercase-forced, max 50 chars
- On apply: calls `pendingPromoCodeProvider.notifier.validate(code)`
- On success: shows applied green banner with code name

**Mutual exclusivity:** The two inputs are mutually exclusive.
- If `pendingPromoCodeProvider != null` → `ReferralCodeInput` is hidden
- If `pendingReferralCodeProvider != null` → `PromoCodeInput` is hidden

### Purchase Flow (`paywall_cta_button.dart`)

Priority order for annual plan purchase:

1. **Pending promo code** → fetch `promoOfferingProvider` → purchase annual package → on success call `pendingPromoCodeProvider.notifier.redeem(code)` → track `promo_code_converted` analytics event
2. **Pending referral code** → existing `discount` offering behavior (unchanged)
3. **Default** → existing default offering behavior (unchanged)

Spin wheel logic is unchanged: `if (spinWheelEnabled && !hasReferral)` — promo code does not suppress spin wheel (they are on different post-purchase paths).

### Deep Link Handling

**Link format:** `nutree://promo?code=SUMMER50`

**If user is authenticated and past onboarding:**
Navigate to paywall with query param `promoCode=SUMMER50`. Paywall reads query param on mount, auto-calls `pendingPromoCodeProvider.notifier.validate(code)`, and pre-fills the `PromoCodeInput` in applied state.

**If user is not yet authenticated:**
Store code in a `deepLinkPromoCodeProvider` (keepAlive string). After auth + onboarding complete, the paywall checks this provider on mount and applies the same validate flow.

---

## Error Handling Summary

| Scenario | Handling |
|---|---|
| Invalid/unknown code | 404 → show "Invalid promo code" in `PromoCodeInput` |
| Code expired | 422 → show "This promo code has expired" |
| Code fully redeemed | 422 → show "This promo code is no longer available" |
| User already redeemed | 422 → show "You've already used this code" |
| Deep link with bad code | Validate fails on paywall mount → show error toast, clear pending code |
| Redeem fails post-purchase | Retry silently (user has RC access); log error for monitoring |

---

## Implementation Sequence

1. Backend: DB models + Alembic migration
2. Backend: domain + repository layer (`PromoCodeRepository`)
3. Backend: command/query handlers (validate, redeem)
4. Backend: API routes + schemas
5. Mobile: providers (`pendingPromoCodeProvider`, `promoOfferingProvider`)
6. Mobile: `PromoCodeInput` widget
7. Mobile: paywall integration (mutual exclusivity + purchase flow)
8. Mobile: deep link handling (router + `deepLinkPromoCodeProvider`)
