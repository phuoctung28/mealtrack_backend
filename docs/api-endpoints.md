# Backend API Endpoints Reference

**Last Updated:** April 17, 2026  
**Base URL:** `http://localhost:8000` (dev) or deployed host  
**API Docs:** `/docs` (Swagger UI)  
**50+ endpoints** across 12 route modules

---

## Health & Monitoring

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Basic health check |
| GET | `/health/db-pool` | DB pool metrics |
| GET | `/health/mysql-connections` | MySQL connection stats |
| GET | `/health/notifications` | FCM health |

---

## Meals

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/meals/image/analyze` | Analyze meal from image |
| POST | `/v1/meals/manual` | Create meal from USDA foods |
| GET | `/v1/meals/{id}` | Get meal details |
| PUT | `/v1/meals/{id}` | Update meal (edit nutrition) |
| DELETE | `/v1/meals/{id}` | Delete meal (soft delete) |
| POST | `/v1/meals/image/immediate` | Upload meal image immediately |

---

## User Profiles

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/user-profiles/me` | Get current user profile |
| PUT | `/v1/user-profiles/me` | Update profile (health metrics) |
| GET | `/v1/user-profiles/tdee` | Calculate TDEE |
| GET | `/v1/user-profiles/{id}` | Get user profile by ID |

---

## Meal Planning

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/meal-plans/weekly/ingredient-based` | Generate 7-day meal plan |
| GET | `/v1/meal-plans/{id}` | Get meal plan |
| PUT | `/v1/meal-plans/{id}` | Update meal plan |
| DELETE | `/v1/meal-plans/{id}` | Delete meal plan |

---

## Meal Suggestions

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/meal-suggestions/generate` | Generate 3 personalized suggestions |
| POST | `/v1/meal-suggestions/discover` | Meal discovery (6 meals/batch) |

---

## Chat (Real-Time)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| WS | `/v1/chat/ws` | WebSocket chat connection |
| POST | `/v1/chat/threads` | Create thread |
| GET | `/v1/chat/threads` | List threads |
| POST | `/v1/chat/threads/{id}/messages` | Send message |
| GET | `/v1/chat/threads/{id}/messages` | Get thread messages |
| DELETE | `/v1/chat/threads/{id}` | Delete thread |

---

## Foods & Ingredients

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/foods/search` | Search USDA foods |
| GET | `/v1/foods/{id}` | Get food details |
| GET | `/v1/ingredients/recognize` | Recognize ingredients (image) |

---

## Notifications

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/notifications/fcm/register` | Register FCM token |
| DELETE | `/v1/notifications/fcm/{token}` | Unregister FCM token |
| GET | `/v1/notifications/preferences` | Get notification preferences |
| PUT | `/v1/notifications/preferences` | Update preferences |

---

## Users

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/users/sync` | Sync user from Firebase |
| PUT | `/v1/users/metrics` | Update user metrics |
| POST | `/v1/users/onboarding` | Complete onboarding |
| DELETE | `/v1/users/me` | Delete user account |

---

## Activities

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/activities` | Create activity |
| GET | `/v1/activities/{id}` | Get activity |
| DELETE | `/v1/activities/{id}` | Delete activity |

---

## Webhooks

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/webhooks/revenucat` | RevenueCat subscription webhook |

---

## Feature Flags

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/feature-flags` | Get feature flags for user |

---

## Response Format

### Success (2xx)
```json
{
  "data": {...},
  "meta": {
    "timestamp": "2026-04-17T12:00:00Z",
    "version": "1.0"
  }
}
```

### Error (4xx, 5xx)
```json
{
  "error": {
    "code": "MEAL_NOT_FOUND",
    "message": "Meal not found",
    "details": {...}
  }
}
```

---

## Authentication

All protected endpoints require Firebase JWT:
```
Authorization: Bearer <firebase-id-token>
```

Dev mode supports `X-Dev-User-Id` header for testing (if `DEV_MODE=true`).

---

See related: `system-architecture.md`, `external-services.md`, `cqrs-guide.md`
