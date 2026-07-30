# Infrastructure & Integrations

Details of external services and infrastructure components.

## External Integrations

| Service | Purpose | Implementation |
|---------|---------|----------------|
| **OpenAI Responses API** | Text & Vision AI | Meal image analysis, food recognition, structured meal parsing |
| **Cloudflare Workers AI** | AI fallback | Alternate text/vision route for configured purposes |
| **pgvector** | Vector cache | Active meal-image-name nearest-neighbor cache |
| **Firebase** | Auth & Messaging | User authentication, push notifications (FCM) |
| **Cloudinary** | Image Storage | CDN and optimized image hosting |
| **RevenueCat** | Subscriptions | Payment and entitlement management |

## Vector Search

The active runtime uses PostgreSQL `pgvector` for meal-image-name
nearest-neighbor matching. Pinecone Phase 05 is historical: no Pinecone adapter,
setting, or dependency is registered in the current runtime.

- **Source of truth**: PostgreSQL/Neon.
- **Use case**: reuse cached image URLs for semantically similar meal names.
- **Fallback**: continue through configured image-search providers when no safe
  vector-cache match exists.

## Database Design

- **Primary DB**: PostgreSQL (Neon)
- **ORM**: SQLAlchemy 2.0 (Async)
- **Migrations**: Alembic
- **Key Tables**: `users`, `user_profiles`, `meal`, `mealimage`, `nutrition`, `food_item`, `food_reference`, `notifications`, `saved_suggestions`, `movement_entries`, `ai_handshake_guest_trial_quotas`.

## Caching

- **Provider**: Redis
- **Strategy**: Selective cache-aside with TTL; default to no cache unless the value has a source of truth, safe stale window, clear invalidation, and correct fallback.
- **Use Cases**: Food search/details, nutrition lookup, short-lived computed read models.
- **Required transient state**: Current meal-suggestion sessions are Redis-backed
  with a four-hour TTL and fail when the session store is unavailable. AI
  Handshake guest trial quota (`ai_handshake_guest_trial_quotas`) remains durable
  product state in PostgreSQL.
- **Do Not Cache**: Notification precompute data, FCM token ownership, meal writes, metric updates.
