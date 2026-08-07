# MealTrack Backend - Project Overview & Product Development Requirements

**Version:** 0.6.8
**Last Updated:** August 7, 2026
**Status:** Current backend product contract. Discover live inventory from `src/`, `tests/`, and `/docs` rather than fixed file counts in this document.

---

## Executive Summary

MealTrack Backend is a FastAPI service for meal tracking, nutrition analysis, hydration, movement, deterministic meal recommendations, and paid web-to-app subscription handoff. It uses 4-layer Clean Architecture with CQRS across API, application, domain, and infrastructure layers, while `src/` also contains root/bootstrap/cron modules outside those layer directories.

---

## 1. Project Vision & Goals

### Vision Statement
Help users understand nutrition with accurate tracking, deterministic recommendations, and reliable AI-assisted meal analysis.

### Primary Goals
1. **Accuracy**: validate AI meal analysis against backend contracts before persistence.
2. **Efficiency**: keep meal logging and recommendation retrieval fast enough for mobile use.
3. **Personalization**: use weekly-budget redistribution, user profile state, and historical affinity.
4. **Operational Safety**: keep required state in durable stores and let optional integrations degrade cleanly.

---

## 2. Core Features

### 1. AI-Powered Meal Analysis
- 6 analysis strategies cover image, portion, ingredient, weight, user-context, and combined flows.
- Nutrition Facts label analysis uses `/v1/meals/food-label/scan-by-url` with optional crop metadata and strict `FoodLabelNutritionResponse` validation.
- OpenAI is the default provider; configured Cloudflare Workers AI can route specific text purposes and vision fallback chains.
- Gemini packages remain in dependencies, but the runtime provider registry is OpenAI + Cloudflare.

### 2. RESTful API
- Meals: image/analyze, upload-token, scan-by-url, food-label/scan-by-url, manual, parse-text, streak, weekly/daily-breakdown, weekly/budget, daily/macros, `/{id}` (GET/DELETE), ingredients (PUT, including optional nutrition overrides), photo replace/delete.
- Meal recommendations: three-day create/replay, compact summary reads, slot detail hydration, swap/log/skip mutations.
- Web funnel: BFF-bound leads, RevenueCat customer correlation, passwordless redemption preflight/finalize.
- User Profiles: create, metrics (GET/POST), TDEE, custom macros.
- Users: sync, Firebase UID lookups, metrics, timezone, language, delete.
- Meal Suggestions: discover, recipes, save.
- Foods: local-first search, details by FDC ID, barcode lookup.
- Hydration: catalog, log, log/drink, daily, weekly, delete.
- Movement: catalog, log, daily, update, delete.
- Weight, nutrition, progress, referrals, promo codes, feature flags, webhooks, monitoring, health, app download, and well-known routes remain active.

### 3. Deterministic Meal Recommendations
- The backend does not call an LLM at recommendation time.
- It ranks curated catalog meals deterministically, stores durable plan state, and exposes compact summary and hydrated slot views.
- `swap`, `log`, and `skip` are owner-scoped and idempotent when the request ID matches.

### 4. Session-Based Meal Suggestions
- Meal suggestions remain separate from catalog-backed recommendations.
- The suggestion flow is still session-based with Redis-backed TTL behavior and language-aware prompt generation.
- This system is additive and does not replace the three-day catalog recommendation flow.

### 5. Local-First Food Search
- Search prefers Redis cache when available, then local `food_reference`, then provider fill.
- Local results are returned first and calories are derived from macros on the backend.
- The active meal-image-name vector cache uses `pgvector`; Pinecone is historical only.

### 6. Hydration, Movement, and Weekly Budget
- Hydration catalog, daily summary, weekly summary, and streak behavior are backed by the current handlers.
- Weekly budget redistribution uses previous-day consumption and is the source of truth for adjusted daily targets.
- Logged movement is included in weekly balance calculations without inflating baseline TDEE.

---

## 3. Technical Stack

- **Framework**: FastAPI 0.136.3 on Python 3.13.2.
- **Database**: PostgreSQL (Neon) with SQLAlchemy 2.0 async runtime.
- **Cache**: Redis 7.0 for selective optional caching and AI-cost optimization; required state is modeled separately.
- **Vector Cache**: `pgvector` for the active meal-image-name vector cache.
- **AI Services**: OpenAI default routing with optional Cloudflare Workers AI fallbacks for configured text and vision purposes.
- **Auth**: Firebase JWT with development bypass guardrails.
- **Event Bus**: PyMediator with singleton registry pattern.
- **Notifications**: Firebase Cloud Messaging with platform-specific configs and deduplication.
- **Subscriptions**: RevenueCat webhook integration plus authenticated web-funnel redemption for web checkout handoff. Legacy direct Paddle fulfillment schema was retired; billing ownership stays with RevenueCat Web.

---

## 4. Non-Functional Requirements

- **Reliability**: external failures should degrade only when the dependency is optional.
- **Test Coverage**: CI enforces 65% unit coverage; the repo keeps high-value paths covered and broad collection remains intentionally noisy until duplicate-package collisions are resolved.
- **Maintainability**: keep files small enough to review, and split docs or code when a file grows past the guardrail.
- **Security**: keep Firebase JWT verification, webhook auth, soft deletes, and input sanitization intact.
- **Performance**: use request-scoped DB sessions, Redis caching where appropriate, and eager loading for queries.
- **Observability**: keep structured error handling and slow-request detection in place.

---

## 5. Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.6.8 | Aug 7, 2026 | Documented paid web redemption, manual nutrition overrides, and stopped hand-maintaining inventory counts in evergreen docs. |
| 0.6.7 | Jul 29, 2026 | Refreshed the project overview with current API surface, deterministic recommendation behavior, hydration semantics, and the pgvector-backed active vector cache. |
| 0.6.6 | Jun 27, 2026 | Documentation refresh for current runtime versions, current codebase metrics, OpenAI-first AI routing, and updated test/CI defaults. |
| 0.6.5 | Jun 13, 2026 | Added validation retry orchestration for structured AI nutrition output, with exactly one repair attempt for meal image scan and text parse flows, controlled `AIOutputValidationError` handling, preserved ingredient-recognition's unstructured contract, and kept calorie divergence checks anchored to backend-derived macro calories. |
| 0.6.4 | Jun 13, 2026 | Added canonical AI nutrition contracts for image and text flows, rejected impossible over-limit food quantities at validation time, preserved current text-parse macro compatibility, and removed silent invalid-food filtering from the legacy parser. |
| 0.6.2 | May 15, 2026 | Configurable referral commissions, custom unit-to-grams fix, BMR floor update, email Universal Links, AsyncUnitOfWork concurrency guard, variable-length referral codes. |
| 0.6.0 | Mar 14, 2026 | Nutrition accuracy rollout, custom macro targets, and adjusted daily target from weekly budget. |
| 0.5.0 | Feb 3, 2026 | Updated metrics across all layers and fixed metric inconsistencies. |
