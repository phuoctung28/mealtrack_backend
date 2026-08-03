# Backend API Endpoints Reference

**Last Updated:** July 29, 2026
**Base URL:** `http://localhost:8000` (dev) or deployed host
**API Docs:** `/docs` (Swagger UI)
**Auth:** Firebase JWT — `Authorization: Bearer <firebase-id-token>`
Dev mode: `X-Dev-User-Id` header (requires `ENVIRONMENT=development` and `ENABLE_DEV_AUTH_BYPASS=1`)
**Surface:** 31 route files, 29 router registrations, 98 standard endpoint decorators, and 2 health `api_route` declarations serving GET+HEAD.

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

The two health routes are declared with `api_route` and answer both GET and HEAD.

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
| GET | `/v1/meals/{meal_id}/value-insights` | Get value-insight cache status or trigger refresh |
| DELETE | `/v1/meals/{meal_id}` | Delete meal (soft delete) |
| PUT | `/v1/meals/{meal_id}/ingredients` | Update meal ingredients |
| PUT | `/v1/meals/{meal_id}/photo` | Replace a meal photo |
| DELETE | `/v1/meals/{meal_id}/photo` | Remove a meal photo |

### Meal Value Insights Contract

- Graph-enabled image scans schedule profile-aware meal value insights after READY meal persistence and meal cache invalidation.
- `GET /v1/meals/{meal_id}/value-insights` is a compatibility/status/refresh endpoint. Existing response statuses are unchanged.
- Graph-disabled scan routes still schedule insights from the API route after the command handler returns.
- Scheduling is best-effort background work and never changes the READY meal response contract.

### Food Label Image Contract

- `/v1/meals/food-label/scan-by-url` accepts a Cloudinary `image_url`/`image_id` pair plus optional `label_crop_image_url`/`label_crop_image_id` and `crop_metadata`.
- The backend downloads image bytes and sends the label crop, or the full image when no crop is supplied, through `FoodLabelImageAnalysisStrategy`.
- AI output is validated against `FoodLabelNutritionResponse` before mapping to `Nutrition` and `food_label_metadata`.
- Failed label reads return controlled validation errors and do not persist meals.
- The backend remains source of truth for validation and calorie presentation; clients must not calculate label nutrition.

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

## Meal Recommendations

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/meal-recommendations/three-day` | Create or replay a 3-day catalog plan; returns compact selected-slot summaries only |
| GET | `/v1/meal-recommendations/{plan_id}` | Read the owner-scoped compact plan summary |
| GET | `/v1/meal-recommendations/{plan_id}/slots/{slot_id}` | Read one hydrated selected slot with alternatives |
| POST | `/v1/meal-recommendations/{plan_id}/slots/{slot_id}/swap` | Swap a slot and return the changed-slot detail response |
| POST | `/v1/meal-recommendations/{plan_id}/slots/{slot_id}/log` | Log the selected recommendation and return the changed-slot detail response |
| POST | `/v1/meal-recommendations/{plan_id}/slots/{slot_id}/skip` | Skip the selected recommendation and return the changed-slot detail response |

### Meal Recommendation Contract

- `create` and `get` return the compact summary contract: selected slots only, with no slot-level ingredients, alternatives, or scores in the plan payload.
- Slot detail hydrates exactly one selected slot plus its alternatives. Mutation responses reuse the same changed-slot shape so clients can patch cached plans in place.
- `swap`, `log`, and `skip` are owner-scoped, idempotent by request ID, and reject already terminal selected slots.
- `shown_at`, `skipped_at`, and `logged_at` are backend-owned outcome fields. Clients must not infer terminal state by recalculating recommendation logic.
- Recommendation analytics are scheduled through `BackgroundTaskManager` when the dependency is available; the route falls back to inline capture when it is not.
- New plan generation uses snapshot-scoped ingredient IDF, confidence-scaled ingredient similarity, and bounded diversity reranking. Existing persisted plans replay their stored candidates and scores. This does not change endpoint paths and does not touch `/v1/meal-suggestions`.
- The existing `Accept-Language` header selects response language (`en`, `vi`, `es`, `fr`, `de`, `ja`, `zh`). For non-English requests, meal names, cuisine, descriptions, and ingredient display names are translated at response time; IDs, units, nutrition, scores, and recommendation state remain canonical.
- Missing/unsupported language, an unset DeepL key, or translation-provider failure returns the successful canonical English response rather than failing the recommendation request.

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
| GET | `/v1/foods/search` | Authenticated local-first food search with provider fill |
| GET | `/v1/foods/autocomplete` | Authenticated local-first autocomplete |
| GET | `/v1/foods/{fdc_id}/details` | Authenticated provider food details by FDC ID |
| GET | `/v1/foods/barcode/{barcode}` | Barcode lookup (cache -> FatSecret -> OpenFoodFacts -> USDA FDC -> estimates) |
| POST | `/v1/ingredients/recognize` | Recognize ingredients from image |
| GET | `/v1/ingredients/health` | Ingredient recognition health |

### Food Search Contract

- Food search routes require Firebase JWT in production and are rate limited.
- Search order is Redis cache, local `food_reference`, then provider fill for remaining limit.
- Local results are returned before provider results, deduped by normalized name, and include `food_reference_id`.
- Redis cache failures are treated as misses for optional food-search caching.
- Provider or translation outages return bounded local results when available.
- Calories in local results are derived from macros with the backend formula:
  `P*4 + max(C-fiber, 0)*4 + fiber*2 + F*9`.

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

Preview responses carry the versioned `calculation_contract`
`onboarding_preview_v2` and `target_revision=0`, because no profile has been
persisted yet. Canonical no-training is `training_days_per_week=0`
and `training_minutes_per_session=0`; `(0, 15)` is legacy compatibility only.
The unauthenticated endpoint rejects bodies over 8 KiB before JSON parsing and
applies an IP-based quota. Keto uses 5/20/75 and calories are derived from the
final macros. Custom targets require a complete triple; reset and target/cache
revision fences keep stale responses from replacing newer targets. Body-fat
projection data is illustrative and source-guarded. Its migration exists but
has not been applied or deployed.

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

## Admin Meal Catalog

Privileged endpoints require Firebase auth and an email in `ADMIN_EMAILS`.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/admin/meal-catalog` | List catalog meals with pagination, search, cuisine, meal type, image, and active filters |
| POST | `/v1/admin/meal-catalog/{catalog_id}/generate-image` | Generate and persist an image URL for a catalog meal that is missing one |

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

## Response Format

Successful responses generally return the route's declared payload directly;
there is no universal `{ "data": ... }` wrapper. Handled application errors use
the following shape:

```json
{
  "detail": {
    "error_code": "MEAL_NOT_FOUND",
    "message": "Meal not found",
    "details": {}
  }
}
```

---

See related: `system-architecture.md`, `external-services.md`, `cqrs-guide.md`
