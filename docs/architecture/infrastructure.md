# Infrastructure & Integrations

Details of external services and infrastructure components.

## External Integrations

| Service | Purpose | Implementation |
|---------|---------|----------------|
| **Google Gemini 2.5 Flash** | Vision AI | Meal image analysis, food recognition |
| **OpenAI GPT-4** | Chat & Planning | Conversational AI, meal plan generation |
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

- **Primary DB**: MySQL 8.0
- **ORM**: SQLAlchemy 2.0 (Async)
- **Migrations**: Alembic (12 migrations)
- **Key Tables**: `users`, `meals`, `nutrition`, `food_items`, `meal_plans`, `chat_threads`, `suggestion_sessions`.

## Caching

- **Provider**: Redis
- **Strategy**: Selective cache-aside with TTL; default to no cache unless the value has a source of truth, safe stale window, clear invalidation, and correct fallback.
- **Use Cases**: Food search/details, nutrition lookup, short-lived computed read models, Gemini explicit cache names.
- **Non-Cache State**: Meal suggestion sessions are transient product state, not cache-aside. Prefer Postgres with `expires_at`, or document Redis as a required state store if retained.
- **Do Not Cache**: Notification precompute data, FCM token ownership, meal writes, metric updates.
