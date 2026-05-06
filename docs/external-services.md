# Backend External Services Integration

**Last Updated:** May 6, 2026
**Services:** Firebase, Cloudinary, Google Gemini, RevenueCat, Redis, Sentry
**All services gracefully degrade on failure** (except Firebase Auth and DB which fail fast)

---

## Firebase

**Purpose:** Authentication + Push Notifications (FCM)

### Authentication
- Firebase Admin SDK for JWT verification
- Dev bypass middleware enabled by `DEV_MODE=true` (`X-Dev-User-Id` header)
- Maps Firebase UID to database UUID

**Config:** `FIREBASE_CREDENTIALS=path/to/credentials.json`

### Firebase Cloud Messaging (FCM)
- Platform-specific configs (Android high priority, APNS alert/badge/sound)
- Multi-device support via `user_fcm_tokens` table
- Deduplication across workers via `notification_sent_log` table (migration 047)

---

## Cloudinary

**Purpose:** Image Storage + CDN

- Folder organization ("mealtrack"), secure URL generation
- Format support: JPEG, PNG
- Fallback to direct URL construction if Resource API unavailable

**Config:** `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

**Used for:** Meal images, user avatars

---

## Google Gemini

**Purpose:** AI Meal Analysis + Content Generation

### Multi-Model Strategy (Rate Distribution)

| Purpose | Model | Env Key |
|---------|-------|---------|
| General / Recipe / Barcode | `gemini-2.5-flash` | `GEMINI_MODEL` |
| Meal names | `gemini-2.5-flash-lite` | `GEMINI_MODEL_NAMES` |
| Recipe primary | `gemini-2.5-flash` | `GEMINI_MODEL_RECIPE_PRIMARY` |
| Recipe secondary | `gemini-2.5-flash` | `GEMINI_MODEL_RECIPE_SECONDARY` |

### Vision AI (Meal Analysis)
- 6 analysis strategies: basic, portion-aware, ingredient-aware, weight-aware, user-context, combined
- JSON parsing with multiple fallbacks: direct, markdown extraction, regex, truncation recovery
- Safety detection for blocked responses

### Token Limits by Use Case

| Use Case | Tokens |
|----------|--------|
| Weekly meal plan | 8000 |
| Meal suggestions (per count, max 8000) | 1500 × count |
| Daily multi-meal | 3000 |
| Single meal | 1500 |

**Config:** `GOOGLE_API_KEY`

---

## RevenueCat

**Purpose:** Subscription Management

- Webhook sync to local `subscriptions` table
- Premium status check with Redis cache fallback
- Signature verification for webhooks
- Webhook events: purchase, renewal, cancellation, expiration

**Config:** `REVENUECAT_SECRET_API_KEY`, `REVENUECAT_WEBHOOK_SECRET`

**Status:** Premium feature gates planned, not currently enforced on routes

---

## Redis Cache

**Purpose:** Session caching, suggestion caching, performance optimization

- **Pattern:** Cache-aside (check → miss → fetch from DB → populate)
- **Connection Pool:** 50 connections | **Default TTL:** 1 hour
- **Error Handling:** Graceful degradation (continue on failure)

**Config:** `REDIS_URL=redis://host:port/db`

### TTL by Data Type

| Data | TTL |
|------|-----|
| User profile | 1 hour |
| Meal suggestions | 4 hours |
| TDEE calculations | 1 hour |
| Food search results | 1 hour |

---

## Sentry Monitoring

**Purpose:** Error tracking, performance profiling, crash reporting

- FastAPI, Starlette, SQLAlchemy integrations built-in
- Gracefully disabled if `SENTRY_DSN` not set

**Config:** `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE=0.1`, `SENTRY_PROFILES_SAMPLE_RATE=0.0`, `SENTRY_SEND_PII=false`

---

## Database (PostgreSQL/MySQL)

See `database-guide.md` for schema, connection pool, and migration details.

**Config:** `DATABASE_URL=mysql+pymysql://user:pass@host/db`

---

## Service Health Checks

```
GET /health                    # Basic health (200 if running)
GET /health/db-pool            # DB pool metrics
GET /health/db-connections     # MySQL connection stats
GET /health/notifications      # FCM health
```

---

## Error Handling & Graceful Degradation

| Service | Failure Mode | Recovery |
|---------|--------------|----------|
| Firebase Auth | Fail fast (401) | Requests rejected |
| MySQL | Fail fast (503) | Requests rejected |
| Gemini | Fail fast (503) | Return error to client |
| Cloudinary | Degrade (fallback URL) | Continue with best-effort image |
| RevenueCat | Degrade (assume premium from cache) | Continue with last-known status |
| Redis | Degrade (bypass cache) | Continue without caching |
| Sentry | Degrade (log locally) | Continue with local logging |

---

See related: `system-architecture.md`, `database-guide.md`, `cqrs-guide.md`
