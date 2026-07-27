# Meal Recommendation Mobile Handoff

Status: backend is MVP-ready for mobile integration once the target environment has catalog data and the feature gate is enabled for test users.

## Feature Summary

The feature recommends 3 meals per day for 3 continuous days:

- Breakfast
- Lunch
- Dinner

The backend does not call an LLM at recommendation time. It uses a curated `meal_catalog`, computes nutrition from `food_reference` ingredients, ranks catalog meals deterministically, and stores a durable plan.

The current mobile contract is compact by default: plan reads return selected slots only, while slot-detail and mutation responses hydrate one slot at a time for local cache patching.

## Backend Engine

Algorithm: deterministic catalog ranking

Core behavior:

1. Load user's timezone and daily calorie target.
2. Allocate calories:
   - Breakfast: 25%
   - Lunch: 37.5%
   - Dinner: 37.5%
3. Load active catalog meals.
4. Score meals by:
   - 82% calorie fit
   - 18% recent ingredient affinity
5. Pick unique selected meals for 9 slots.
6. Store alternatives for each slot so user can swap.

## Required Mobile Flow

On app open or recommendation screen entry:

1. Call `POST /v1/meal-recommendations/three-day`.
2. Use a stable `Idempotency-Key` for the current auto-generation attempt.
3. Cache the returned compact plan summary by `plan_id` and render the selected slots immediately.
4. Let user:
   - view meal details
   - swap a slot
   - log a recommended meal
5. Fetch `GET /v1/meal-recommendations/{plan_id}/slots/{slot_id}` when the user drills into a slot or needs alternatives.
6. Merge swap/log responses back into the cached plan instead of reloading the full plan.

## API Contracts

All endpoints require normal Firebase auth.

### Create Or Replay 3-Day Plan

```http
POST /v1/meal-recommendations/three-day
Idempotency-Key: mobile-generated-stable-key
X-Timezone: America/Los_Angeles
Authorization: Bearer <firebase-jwt>
```

Request body: none.

Behavior:

- Creates a new active 3-day plan if needed.
- Replays the same plan for the same `Idempotency-Key`.
- Supersedes prior active plan for the user when creating a new one.

### Get Existing Plan

```http
GET /v1/meal-recommendations/{plan_id}
Authorization: Bearer <firebase-jwt>
```

Behavior:

- Returns the compact plan summary for the owner-scoped plan.
- The response includes selected slots only. Slot ingredients, alternatives, and scores are omitted from the summary payload.

### Swap Slot

```http
POST /v1/meal-recommendations/{plan_id}/slots/{slot_id}/swap
Authorization: Bearer <firebase-jwt>
```

```json
{
  "request_id": "mobile-stable-swap-request-id",
  "expected_selection_version": 1,
  "alternative_catalog_meal_id": "optional-catalog-meal-id",
  "reason": "user_requested"
}
```

Notes:

- `expected_selection_version` prevents stale swaps.
- If `alternative_catalog_meal_id` is omitted, backend chooses the next best alternative.
- Automatic swaps consume unseen candidates stored for that slot. After the pool is
  exhausted, the backend replenishes only that slot with five fresh candidates;
  previously seen candidates remain auditable but are never selected again.
- Use a stable `request_id` for retry safety.

### Log Recommended Meal

```http
POST /v1/meal-recommendations/{plan_id}/slots/{slot_id}/log
Authorization: Bearer <firebase-jwt>
```

```json
{
  "request_id": "mobile-stable-log-request-id"
}
```

Behavior:

- Materializes the selected catalog meal as a normal meal using the already loaded selected catalog projection.
- Preserves ingredient `food_reference_id`.
- Marks the recommendation slot as logged.
- Safe to retry with the same `request_id`.

## Response Shape

The plan summary is compact:

- plan metadata: `id`, `status`, `timezone`, `start_date`, `daily_calories`, `allergy_evaluated`
- slot summary: `id`, `slot_date`, `day_index`, `meal_type`, `catalog_meal_id`, compact `catalog_meal`, `target_calories`, `position`, `selection_version`, `logged_meal_id`
- omitted from plan summary: `score`, `alternatives`, and `catalog_meal.ingredients`

Use `GET /v1/meal-recommendations/{plan_id}/slots/{slot_id}` for the hydrated selected slot payload when the user needs details or alternatives.

## Error Handling

Mobile should handle:

- `404`: feature disabled for user or plan not found.
- `400`: invalid idempotency key or request payload.
- `409`: stale `selection_version`, duplicate/conflicting idempotency request, already logged slot.
- `503`: user calorie target unavailable or insufficient catalog coverage.

## Backend Readiness

Ready:

- Four-table local schema is simplified.
- Catalog importer exists.
- Catalog nutrition is computed from ingredients and `food_reference`.
- Deterministic 3-day recommendation engine exists.
- Create, get, slot-detail, swap, and log endpoints exist.
- Operation idempotency exists.
- Recommendation read paths now use the compact/delta contract for mobile cache patching.
- Candidate lifecycle state (`seen_at` and `retired_at`) is backend-owned; the
  existing slot detail response remains unchanged, so no Flutter source change is required.
- Replenishment emits the same delta response and must be staged with database-pool
  and latency observation before production enablement. Daily readiness/cron remain deferred.
- Focused backend tests pass.

Environment prerequisites:

- Full production catalog import is not complete; live dev DB currently has only the first imported sample set.
- Recommendation endpoints are available without a backend rollout gate.

## Mobile Team Can Start Now

Mobile can start:

- screen structure for 3-day plan
- local state model for compact plan + hydrated slot detail state
- API client methods
- idempotency key generation
- swap/log retry behavior
- loading/error/empty states
- rendering selected meal cards from summary data and alternative cards from hydrated slot detail
