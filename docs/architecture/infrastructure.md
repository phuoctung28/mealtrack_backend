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
- **Strategy**: Cache-Aside with TTL
- **Use Cases**: User profiles, session-based suggestions (4h TTL), feature flags.
