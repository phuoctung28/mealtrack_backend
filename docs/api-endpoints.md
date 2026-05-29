# Backend API Endpoints Reference

**Last Updated:** May 27, 2026
**Base URL:** `http://localhost:8000` (dev) or deployed host
**API Docs:** `/docs` (Swagger UI)
**Auth:** Firebase JWT — `Authorization: Bearer <firebase-id-token>`
Dev mode: `X-Dev-User-Id` header (requires `DEV_MODE=true`)

---

## Health & Monitoring

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Basic health check |
| GET | `/health/db-pool` | DB pool metrics |
| GET | `/health/db-connections` | DB connection stats |
| GET | `/health/notifications` | FCM health |
| GET | `/v1/monitoring/cache/metrics` | Redis cache metrics |

## App & Universal Links

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/app-download` | Redirect to App Store with `?source=` campaign tracking |
| GET | `/.well-known/apple-app-site-association` | iOS Universal Links config (paths: /log, /dashboard, /upgrade, /feedback, /settings) |

---

## Meals

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/meals/image/analyze` | Analyze meal from image (immediate upload) |
| POST | `/v1/meals/manual` | Create meal from USDA foods |
| POST | `/v1/meals/parse-text` | Parse meal from text description |
| GET | `/v1/meals/streak` | Get meal logging streak |
| GET | `/v1/meals/weekly/daily-breakdown` | Weekly daily nutrition breakdown |
| GET | `/v1/meals/weekly/budget` | Weekly calorie budget |
| GET | `/v1/meals/daily/macros` | Today's aggregated macros |
| GET | `/v1/meals/{meal_id}` | Get meal details |
| DELETE | `/v1/meals/{meal_id}` | Delete meal (soft delete) |
| PUT | `/v1/meals/{meal_id}/ingredients` | Update meal ingredients |

---

## User Profiles

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/user-profiles/` | Create user profile |
| GET | `/v1/user-profiles/metrics` | Get current user metrics |
| POST | `/v1/user-profiles/metrics` | Update metrics + recalculate TDEE |
| GET | `/v1/user-profiles/tdee` | Get TDEE calculation |
| PUT | `/v1/user-profiles/custom-macros` | Set custom macro targets |

---

## Users

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/users/sync` | Sync user from Firebase |
| GET | `/v1/users/firebase/{firebase_uid}` | Get user profile by Firebase UID |
| GET | `/v1/users/firebase/{firebase_uid}/status` | Get user status |
| PUT | `/v1/users/firebase/{firebase_uid}/last-accessed` | Update last accessed |
| PUT | `/v1/users/metrics` | Update user metrics |
| PUT | `/v1/users/timezone` | Update user timezone |
| PATCH | `/v1/users/language` | Update user language |
| DELETE | `/v1/users/firebase/{firebase_uid}` | Delete user account |

---

## Meal Suggestions

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/meal-suggestions/generate` | Generate 3 personalized suggestions |
| POST | `/v1/meal-suggestions/discover` | Meal discovery (6 meals/batch with images) |
| POST | `/v1/meal-suggestions/recipes` | Generate recipe batch |
| POST | `/v1/meal-suggestions/save` | Save a meal suggestion |

---

## Saved Suggestions

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/saved-suggestions` | List saved suggestions |
| POST | `/v1/saved-suggestions` | Save a suggestion |
| DELETE | `/v1/saved-suggestions/{suggestion_id}` | Remove saved suggestion |

---

## Foods & Ingredients

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/foods/search` | Search USDA foods |
| GET | `/v1/foods/{fdc_id}/details` | Get food details by FDC ID |
| GET | `/v1/foods/barcode/{barcode}` | Barcode lookup (6-step cascade) |
| POST | `/v1/ingredients/recognize` | Recognize ingredients from image |

---

## TDEE

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/tdee/preview` | Preview TDEE calculation without saving |

---

## Weight Entries

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/weight-entries` | List weight entries |
| POST | `/v1/weight-entries` | Log weight entry |
| DELETE | `/v1/weight-entries/{entry_id}` | Delete weight entry |
| POST | `/v1/weight-entries/sync` | Sync weight entries |

---

## Activities

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/activities/daily` | Get daily activities |

---

## Notifications

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/notifications/tokens` | Register FCM token |
| DELETE | `/v1/notifications/tokens` | Unregister FCM token |
| GET | `/v1/notifications/preferences` | Get notification preferences |
| PUT | `/v1/notifications/preferences` | Update preferences |

---

## Referrals

Codes are 3–15 characters. Commission rates set via `REFERRAL_COMMISSIONS` env var. See `external-services.md`.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/referrals/validate` | Validate referral code |
| POST | `/v1/referrals/apply` | Apply referral code |
| GET | `/v1/referrals/my-code` | Get user's referral code |
| GET | `/v1/referrals/stats` | Get referral stats |
| POST | `/v1/referrals/payout` | Request referral payout |

---

## Cheat Days

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/cheat-days` | List cheat days |
| POST | `/v1/cheat-days` | Mark a cheat day |
| DELETE | `/v1/cheat-days/{date_str}` | Remove cheat day |

---

## Feature Flags

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/feature-flags/` | List all feature flags |
| GET | `/v1/feature-flags/{feature_name}` | Get individual flag |
| POST | `/v1/feature-flags/` | Create feature flag |
| PUT | `/v1/feature-flags/{feature_name}` | Update feature flag |

---

## Codes

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/codes/validate` | Validate promo or referral code before purchase (does not redeem) |

---

## Webhooks

Handles RevenueCat lifecycle events (INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION, BILLING_ISSUE, PRODUCT_CHANGE, REFUND, TRANSFER). Signature verified via constant-time HMAC; events mirrored to PostHog when `POSTHOG_API_KEY` is set.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/webhooks/revenuecat` | RevenueCat subscription webhook |
| GET | `/v1/webhooks/revenuecat/health` | Webhook health check |

---

## Response Format

```json
// Success (2xx)
{ "data": {...} }

// Error (4xx, 5xx)
{ "error": { "code": "MEAL_NOT_FOUND", "message": "Meal not found" } }
```

---

See related: `system-architecture.md`, `external-services.md`, `cqrs-guide.md`
