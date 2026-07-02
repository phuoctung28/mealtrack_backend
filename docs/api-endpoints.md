# Backend API Endpoints Reference

**Last Updated:** July 2, 2026
**Base URL:** `http://localhost:8000` (dev) or deployed host
**API Docs:** `/docs` (Swagger UI)
**Auth:** Firebase JWT — `Authorization: Bearer <firebase-id-token>`
Dev mode: `X-Dev-User-Id` header (requires `DEV_MODE=true`)
**Surface:** 28 route files, 27 router registrations, 26 endpoint-bearing route modules, and 85 endpoint decorators.

---

## Health & Monitoring

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Basic health check |
| GET | `/v1/health` | Versioned health check |
| GET | `/v1/health/db-pool` | DB pool metrics |
| GET | `/v1/health/db-connections` | DB connection stats |
| GET | `/v1/health/notifications` | FCM health |
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
| POST | `/v1/meals/food-label/analyze` | Analyze Nutrition Facts label from image upload |
| GET | `/v1/meals/upload-token` | Create signed direct-upload token |
| POST | `/v1/meals/scan-by-url` | Analyze meal from an existing image URL |
| POST | `/v1/meals/food-label/scan-by-url` | Analyze Nutrition Facts label from an existing image URL |
| POST | `/v1/meals/manual` | Create meal from USDA foods |
| POST | `/v1/meals/parse-text` | Parse meal from text description |
| POST | `/v1/meals/parse-text/guest-trial` | One-shot guest text parse trial |
| GET | `/v1/meals/streak` | Get meal logging streak |
| GET | `/v1/meals/weekly/daily-breakdown` | Weekly daily nutrition breakdown |
| GET | `/v1/meals/weekly/budget` | Weekly calorie budget |
| GET | `/v1/meals/daily/macros` | Today's aggregated macros |
| GET | `/v1/meals/{meal_id}` | Get meal details |
| DELETE | `/v1/meals/{meal_id}` | Delete meal (soft delete) |
| PUT | `/v1/meals/{meal_id}/ingredients` | Update meal ingredients |

### Food Label OCR Contract

- `/v1/meals/food-label/scan-by-url` accepts optional `ocr_text_lines` from native client OCR.
- When `FOOD_LABEL_OCR_FIRST_ENABLED=true`, the backend attempts deterministic parsing before AI image analysis.
- OCR parse failures, sparse text, missing fields, and conflicting values fall back to the existing AI image path.
- The backend remains source of truth for validation and derives calories from macros; clients must not calculate label nutrition.

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
| PUT | `/v1/users/firebase/{firebase_uid}/onboarding/complete` | Complete onboarding |
| PUT | `/v1/users/timezone` | Update user timezone |
| PATCH | `/v1/users/language` | Update user language |
| DELETE | `/v1/users/firebase/{firebase_uid}` | Delete user account |

---

## Meal Suggestions

| Method | Endpoint | Purpose |
|--------|----------|---------|
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
| GET | `/v1/foods/barcode/{barcode}` | Barcode lookup (cache -> FatSecret -> OpenFoodFacts -> USDA FDC -> estimates) |
| POST | `/v1/ingredients/recognize` | Recognize ingredients from image |
| GET | `/v1/ingredients/health` | Ingredient recognition health |

### Barcode Lookup Contract

- Accepts numeric GTIN-8/12/13/14 values with a valid check digit; malformed input returns 400 before external calls.
- Valid GTIN misses return 404.
- Verified sources are `cache`, `fatsecret`, `openfoodfacts`, and `usda_fdc`.
- `brave_search`, `fatsecret_name_search`, and `ai_estimate` are editable estimates with `is_estimate=true` and are not written to the global catalog.
- Cached responses may include `provider_source` to expose the original provider behind `source=cache`.

---

## Hydration

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/hydration/catalog` | Get drink catalog |
| POST | `/v1/hydration/log` | Log water intake |
| POST | `/v1/hydration/log/drink` | Log caloric drink intake |
| GET | `/v1/hydration/daily` | Daily hydration summary |
| GET | `/v1/hydration/weekly` | Weekly hydration summary |
| DELETE | `/v1/hydration/{entry_id}` | Delete hydration entry |

---

## Movement

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/movement/catalog` | Get movement activity catalog |
| POST | `/v1/movement/log` | Log movement entry |
| GET | `/v1/movement/daily` | Daily movement summary |
| PATCH | `/v1/movement/{entry_id}` | Update movement entry |
| DELETE | `/v1/movement/{entry_id}` | Delete movement entry |

---

## Nutrition

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/nutrition/bulk` | Bulk nutrition lookup |
| GET | `/v1/nutrition/presence` | Get activity/nutrition presence |

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
| GET | `/v1/activities/bulk` | Get activities for multiple days |

---

## Progress

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/progress/journey` | Action-based journey progress snapshot for the dashboard card |

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

## Promo Codes

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/promo-codes/validate` | Validate promo code |
| POST | `/v1/promo-codes/redeem` | Redeem promo code |

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
