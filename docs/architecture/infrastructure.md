# Infrastructure & Integrations

Details of external services and infrastructure components.

## External Integrations

| Service | Purpose | Implementation |
|---------|---------|----------------|
| **OpenAI Responses API** | Text & Vision AI | Meal image analysis, food recognition, structured meal parsing |
| **Cloudflare Workers AI** | AI fallback | Alternate text/vision route for configured purposes |
| **Pinecone** | Vector Database | Semantic food search (1024-dim vectors) |
| **Firebase** | Auth & Messaging | User authentication, push notifications (FCM) |
| **Cloudinary** | Image Storage | CDN and optimized image hosting |
| **RevenueCat** | Subscriptions | Payment and entitlement management |

## Vector Search (Pinecone Phase 05)

The system uses Pinecone Inference API with the `llama-text-embed-v2` model.

- **Dimensions**: 1024
- **Indexes**: `ingredients` (per-100g data), `usda` (fallback database)
- **Logic**: Search `ingredients` first (threshold 0.35); fallback to `usda` if score < 0.6.

## Database Design

- **Primary DB**: PostgreSQL (Neon)
- **ORM**: SQLAlchemy 2.0 (Async)
- **Migrations**: Alembic
- **Key Tables**: `users`, `user_profiles`, `meal`, `mealimage`, `nutrition`, `food_item`, `food_reference`, `notifications`, `saved_suggestions`, `movement_entries`, `ai_handshake_guest_trial_quotas`.

## Caching

- **Provider**: Redis
- **Strategy**: Selective cache-aside with TTL; default to no cache unless the value has a source of truth, safe stale window, clear invalidation, and correct fallback.
- **Use Cases**: Food search/details, nutrition lookup, short-lived computed read models.
- **Non-Cache State**: Meal suggestion sessions are transient product state, not cache-aside. Prefer Postgres with `expires_at`, or document Redis as a required state store if retained. AI Handshake guest trial quota (`ai_handshake_guest_trial_quotas`) is durable product state stored in Postgres — Redis is not required for it.
- **Do Not Cache**: Notification precompute data, FCM token ownership, meal writes, metric updates.
