# Backend External Services Integration

**Last Updated:** April 17, 2026  
**Services:** Firebase, Cloudinary, Google Gemini, Pinecone, RevenueCat, MySQL, Redis, Sentry  
**All services gracefully degrade on failure** (except auth and DB which fail fast)

---

## Firebase

**Purpose:** Authentication + Push Notifications (FCM)

### Authentication
- Firebase Admin SDK for JWT verification
- Dev bypass middleware for local development
- Token expiration and revocation checks
- Maps Firebase UID to database UUID

**Configuration:**
```
FIREBASE_CREDENTIALS=path/to/credentials.json
```

### Firebase Cloud Messaging (FCM)
- Platform-specific configs (Android high priority, APNS alert/badge/sound)
- Multi-device support via `user_fcm_tokens` table
- Failed token tracking with error codes
- Deduplication across workers via `notification_sent_log` table (migration 047)

---

## Cloudinary

**Purpose:** Image Storage + CDN

**Features:**
- Folder organization ("mealtrack")
- Secure URL generation
- Format support (JPEG, PNG)
- Resource API with fallback to direct URL construction

**Configuration:**
```
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

**Used For:** Meal images, user avatars

---

## Google Gemini

**Purpose:** AI Meal Analysis + Chat + Content Generation

### Multi-Model Strategy (Rate Distribution)
| Model | Purpose | Rate Limit |
|-------|---------|------------|
| gemini-2.5-flash-lite | Meal names | 10 RPM |
| gemini-2.5-flash | Recipe primary | 5 RPM |
| gemini-3-flash | Recipe secondary (load distribution) | — |
| Default | General fallback | — |

### Vision AI (Meal Analysis)
- 6 analysis strategies: basic, portion-aware, ingredient-aware, weight-aware, user-context, combined
- JSON parsing with multiple fallbacks: direct, markdown extraction, regex, truncation recovery
- Safety detection for blocked responses

### Token Optimization
| Use Case | Tokens |
|----------|--------|
| Weekly meal plan | 8000 |
| Meal suggestions (per count, max 8000) | 1500 × count |
| Daily multi-meal | 3000 |
| Single meal | 1500 |

**Configuration:**
```
GOOGLE_API_KEY=...
```

**Used For:** Meal image analysis, meal generation, chat responses

---

## Pinecone

**Purpose:** Vector Search for Ingredient Nutrition Data

**Configuration:**
- **Embedding Model:** llama-text-embed-v2 (1024 dimensions)
- **Indexes:** "ingredients", "usda"
- **Similarity Threshold:** 0.35

**Features:**
- Semantic ingredient search
- Nutrition scaling by portion
- Unit conversion (g, kg, oz, lb, ml, cup, tbsp, tsp, etc.)
- Aggregate nutrition calculation

**Configuration:**
```
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...
```

**Status:** Deprecated in favor of direct USDA/AI lookup (still available for fallback)

---

## RevenueCat

**Purpose:** Subscription Management

**Features:**
- Webhook sync to local `subscriptions` table
- Premium status check with cache fallback
- Signature verification for webhooks
- Webhook events: purchase, renewal, cancellation, expiration

**Configuration:**
```
REVENUECAT_API_KEY=...
REVENUECAT_WEBHOOK_SECRET=...
```

**Used For:** Premium feature gates (planned, not currently enforced)

---

## MySQL Database

**Engine:** MySQL 8.0 + SQLAlchemy 2.0

**Configuration:**
```
DATABASE_URL=mysql+pymysql://user:pass@host/db
```

### Connection Pool
- **Min connections:** 20
- **Overflow:** 10 additional connections under load
- **Timeout:** Connection timeout handling with retry logic

### Schema
| Table | Purpose |
|-------|---------|
| users | Firebase UID mapping, auth |
| user_profiles | Health metrics, goals, preferences |
| subscriptions | RevenueCat cache |
| meal | Meal records with state machine |
| meal_image | Cloudinary references |
| nutrition | Macros + confidence score |
| food_item | Ingredients with density conversion |
| meal_plan | Weekly/daily plans |
| meal_plan_day | Day details |
| planned_meal | Individual planned meals |
| notification_preferences | User notification settings |
| user_fcm_tokens | Firebase Cloud Messaging tokens |
| chat_threads | Conversation storage |
| chat_messages | Message storage |
| notification_sent_log | Deduplication for FCM (migration 047) |

### Migrations
- Managed via Alembic
- Auto-migrate on startup with retry logic
- Recent: notifications (047), onboarding (045), fiber/sugar (034), custom macros (037)

---

## Redis Cache

**Purpose:** Session caching, suggestion caching, performance optimization

**Configuration:**
```
REDIS_URL=redis://host:port/db
```

### Cache Strategy
- **Pattern:** Cache-aside (check cache → miss → fetch from DB → populate cache)
- **Serialization:** JSON with Pydantic support
- **Connection Pool:** 50 connections
- **Default TTL:** 1 hour
- **Error Handling:** Graceful degradation (continue on cache failure)

### TTL by Data Volatility
| Data | TTL |
|------|-----|
| User profile | 1 hour |
| Meal suggestions | 4 hours |
| TDEE calculations | 1 hour |
| Food search results | 1 hour |

**Used For:**
- Session-based meal suggestions (4h)
- User profile caching
- TDEE calculation caching
- Food reference caching

---

## Sentry Monitoring

**Purpose:** Error tracking, performance profiling, crash reporting

**Configuration:**
```
SENTRY_DSN=...
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

### Features
- Error tracking with context and breadcrumbs
- Performance monitoring (traces)
- Profiling (CPU, memory)
- FastAPI, Starlette, SQLAlchemy integrations
- Source map support
- PII handling (disabled by default)

**Status:** NEW in Apr 2026, gracefully disabled if DSN not set

---

## Service Health Checks

```bash
GET /health               # Basic health (200 if running)
GET /health/db-pool       # DB pool metrics
GET /health/mysql-connections  # MySQL connection stats
GET /health/notifications # FCM health
```

---

## Error Handling & Graceful Degradation

| Service | Failure Mode | Recovery |
|---------|--------------|----------|
| Firebase Auth | Fail fast (401) | Requests rejected |
| Cloudinary | Degrade (use fallback URL) | Continue with best-effort image |
| Gemini | Fail fast (503) | Return error to client |
| Pinecone | Degrade (use USDA/AI fallback) | Continue with alternative source |
| RevenueCat | Degrade (assume premium from cache) | Continue with last-known status |
| MySQL | Fail fast (503) | Requests rejected |
| Redis | Degrade (bypass cache) | Continue without caching |
| Sentry | Degrade (log locally) | Continue with local logging |

---

See related: `system-architecture.md`, `database-guide.md`, `cqrs-guide.md`
