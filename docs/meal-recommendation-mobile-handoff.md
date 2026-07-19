# Meal Recommendation Mobile Handoff

Status: backend is MVP-ready for mobile integration once the target environment has catalog data and the feature gate is enabled for test users.

## Feature Summary

The feature recommends 3 meals per day for 3 continuous days:

- Breakfast
- Lunch
- Dinner

The backend does not call an LLM at recommendation time. It uses a curated `meal_catalog`, computes nutrition from `food_reference` ingredients, ranks catalog meals deterministically, and stores a durable plan.

## Backend Engine

Algorithm: `catalog_deterministic_v1`

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
3. Render returned 3-day plan.
4. Let user:
   - view meal details
   - swap a slot
   - log a recommended meal
5. Re-read the plan with `GET /v1/meal-recommendations/{plan_id}` when needed.

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

- Materializes the selected catalog meal as a normal meal.
- Preserves ingredient `food_reference_id`.
- Marks the recommendation slot as logged.
- Safe to retry with the same `request_id`.

## Response Shape

The recommendation response is display-complete. Each selected slot and alternative includes renderable catalog meal details.

```json
{
  "id": "plan-id",
  "status": "active",
  "timezone": "America/Los_Angeles",
  "start_date": "2026-07-17",
  "daily_calories": 2000,
  "algorithm_version": "catalog_deterministic_v1",
  "allergy_evaluated": false,
  "slots": [
    {
      "id": "slot-id",
      "slot_date": "2026-07-17",
      "day_index": 0,
      "meal_type": "breakfast",
      "catalog_meal_id": "catalog-meal-id",
      "catalog_meal": {
        "id": "catalog-meal-id",
        "name": "Teriyaki Chicken Rice",
        "cuisine": "japanese",
        "description": "Display copy",
        "image_url": "https://...",
        "calories": 640,
        "macros": {
          "protein_g": 38.5,
          "carbs_g": 72.1,
          "fat_g": 18.3,
          "fiber_g": 4.2,
          "sugar_g": 8.1
        },
        "ingredients": [
          {
            "food_reference_id": 123,
            "display_name": "Chicken breast",
            "quantity": 120,
            "unit": "g"
          }
        ]
      },
      "target_calories": 500,
      "score": 0.94,
      "position": 0,
      "selection_version": 1,
      "logged_meal_id": null,
      "alternatives": [
        {
          "id": "candidate-id",
          "catalog_meal_id": "alternative-catalog-meal-id",
          "catalog_meal": {
            "id": "alternative-catalog-meal-id",
            "name": "Chicken Rice Bowl",
            "cuisine": "vietnamese",
            "description": "Display copy",
            "image_url": "https://...",
            "calories": 590,
            "macros": {
              "protein_g": 34.2,
              "carbs_g": 68.0,
              "fat_g": 16.5,
              "fiber_g": 3.8,
              "sugar_g": 5.4
            },
            "ingredients": []
          },
          "score": 0.91,
          "candidate_rank": 1
        }
      ]
    }
  ]
}
```

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
- Create, get, swap, and log endpoints exist.
- Operation idempotency exists.
- Recommendation responses include renderable selected and alternative meal details.
- Focused backend tests pass.

Environment prerequisites:

- Full production catalog import is not complete; live dev DB currently has only the first imported sample set.
- Recommendation endpoints are available without a backend rollout gate.

## Mobile Team Can Start Now

Mobile can start:

- screen structure for 3-day plan
- local state model for plan/slot/alternative/logged state
- API client methods
- idempotency key generation
- swap/log retry behavior
- loading/error/empty states
- rendering selected meal cards and alternative cards from embedded `catalog_meal`
