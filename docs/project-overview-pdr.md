# MealTrack Backend - Project Overview & Product Development Requirements

**Version:** 0.6.4
**Last Updated:** June 17, 2026
**Status:** Production-ready. 620 Python files and ~52.6K LOC in `src/`; current suite has 291 Python test files and 1,600+ collected tests. Latest: async PostgreSQL/Neon runtime alignment, observability connector, normalized database foundation, hydration/movement APIs, affiliate outbox, and refreshed codebase documentation.

---

## Executive Summary

MealTrack Backend is a FastAPI service powering meal tracking, nutritional analysis, weekly calorie budgeting, hydration, movement, referrals, promo codes, notifications, and subscription state. It implements Clean Architecture with CQRS across API, application, domain, and infrastructure layers, integrating Gemini-based AI meal analysis, PostgreSQL/pgvector storage, Redis-backed optional cache-aside paths, and operational observability. The current HTTP surface has 26 router registrations and 83 endpoint decorators across meals, users, profiles, suggestions, hydration, movement, nutrition, referrals, promo codes, health, monitoring, webhooks, and support routes.

---

## 1. Project Vision & Goals

### Vision Statement
Empower users to understand their nutrition through effortless, AI-driven tracking and personalized recommendations.

### Primary Goals
1. **Accuracy**: >90% food recognition accuracy via Gemini Vision.
2. **Efficiency**: Meal logging in < 30 seconds.
3. **Personalization**: Goal-based (CUT, BULK, RECOMP) nutritional targets.
4. **Performance**: API p95 < 500ms.

---

## 2. Core Features

### 1. AI-Powered Meal Analysis
- 6 analysis strategies: basic, portion-aware, ingredient-aware, weight-aware, user-context-aware, combined.
- Multi-food detection in single image with confidence scoring.
- Gemini 2.5 Flash with strategy pattern for flexible context handling.
- Returns results in <3 seconds through state machine (PROCESSING → ANALYZING → READY/FAILED).

### 2. RESTful API (83 Endpoint Decorators across 26 Router Registrations)
- **Meals**: image/analyze, upload-token, scan-by-url, manual, parse-text, streak, weekly/daily-breakdown, weekly/budget, daily/macros, /{id} (GET/DELETE), ingredients (PUT).
- **User Profiles**: create, metrics (GET/POST), TDEE, custom-macros.
- **Users**: sync, Firebase UID lookups, onboarding completion, timezone, language, delete.
- **Meal Suggestions**: discover (6 meals + images), recipes, save.
- **Saved Suggestions**: list, save, delete.
- **Foods**: USDA FDC search, details by FDC ID, barcode lookup (6-step cascade).
- **Ingredients**: image-based recognition, health.
- **TDEE**: preview calculation.
- **Weight Entries**: list, log, delete, sync.
- **Activities**: daily and bulk activities.
- **Hydration**: drink catalog, water logging, caloric drink logging, daily/weekly summaries, delete.
- **Movement**: activity catalog, log, daily summary, update, delete.
- **Nutrition**: bulk nutrition lookup and activity presence.
- **Notifications**: FCM token management, deduplication (notification_sent_log), preferences.
- **Referrals**: validate, apply, my-code, stats, payout.
- **Promo Codes / Codes**: validate/redeem promo codes and validate purchase codes.
- **Cheat Days**: list, mark, delete.
- **Feature Flags**: CRUD for feature toggles.
- **Webhooks**: RevenueCat subscription sync.
- **Monitoring**: cache metrics.
- **Health**: health, db-pool, db-connections, notifications.

### 3. Session-Based Meal Suggestions & Discovery
- Generates 3 personalized suggestions per session with Redis 4h TTL.
- Portion multipliers (1-4x) and rejection feedback loop.
- Multi-language support (7 languages: en, vi, es, fr, de, ja, zh) with fallback.
- Language-aware prompt generation with injected instructions.
- Meal discovery endpoint: 6 meals/batch with image search (Unsplash, Pexels) for visual browsing.

### 4. Intelligent Meal Planning
- AI-generated 7-day plans using available ingredients only.
- Dietary restrictions (9 preferences: vegan, vegetarian, keto, paleo, etc.).
- Cooking time constraints (weekday 30min, weekend 60min).
- Min 3 days before meal repetition, max 2 same-cuisine per week.

### 5. Food Discovery & Vector-Backed Image Cache
- PostgreSQL/pgvector-backed local runtime for vector-capable storage.
- Meal image cache uses SigLIP embeddings and configurable cosine thresholds for image reuse.
- Nutrition scaling by portion with unit conversion (g, kg, oz, lb, ml, cup, etc.).
- Aggregated nutrition calculation across multiple ingredients.

### 6. Nutrition Accuracy & Integrity (NEW)
- **Fiber-Aware Calorie Formula**: `P×4 + (C-fiber)×4 + fiber×2 + F×9` instead of simple `P×4 + C×4 + F×9`.
- **Density-Based Conversion**: 30+ food density constants (ml↔g) for accurate volume-to-mass conversion (honey 1.42, oil 0.92, milk 1.03).
- **Macro Validation Service**: Post-generation validation of AI macros, corrects calories if >10% divergent from formula.
- **Custom Macro Targets**: Users can override calculated macros with custom protein/carb/fat targets per profile.
- **Food Reference Evolution**: Dual-lookup (barcode_products + food_reference) for backward compatibility during food data migration.

### 7. Adjusted Daily Target & Weekly Budget
- Weekly budget stored per user with remaining_days calculation (Mon=7, Sun=1).
- Adjusted daily target redistributes weekly budget based on previous days' consumption.
- Used by meal suggestions, meal plans, and nutrition tracking features.
- BMR floor (85% of standard daily, raised from 80%) protects against dangerously low targets. Clinical minimums: 1200 kcal (female), 1500 kcal (male). Cutting deficit: 300 kcal (~0.3 kg/week).

---

## 3. Technical Stack
- **Framework**: FastAPI 0.115+ (Python 3.11+)
- **Database**: PostgreSQL (Neon) with SQLAlchemy 2.0 async runtime, asyncpg, Alembic, and pgvector-enabled local compose
- **Cache**: Redis 7.0 for selective optional caching and AI-cost optimization; required state must be modeled separately
- **AI Services**: Google Gemini 2.5 Flash (multi-model for rate distribution)
- **Storage**: Cloudinary (image storage with folder organization)
- **Image Search**: Unsplash + Pexels adapters (meal discovery)
- **Auth**: Firebase JWT with development bypass middleware
- **Event Bus**: PyMediator with singleton registry pattern
- **Notifications**: Firebase Cloud Messaging (FCM) with platform-specific configs + deduplication
- **Subscriptions**: RevenueCat webhook integration
- **Monitoring**: Sentry SDK (error tracking, performance profiling)

---

## 4. Non-Functional Requirements
- **Reliability**: 99.9% uptime with graceful degradation for external services.
- **Test Coverage**: 70%+ overall target, 100% critical paths, 80%+ for new features.
- **Maintainability**: <200 LOC per file, 4-Layer Clean Architecture with strict separation.
- **Security**: Firebase JWT verification, RevenueCat webhook auth, soft deletes, input sanitization.
- **Performance**: Request-scoped DB sessions, Redis caching with TTL, eager loading for queries.
- **Scalability**: Dynamic connection pool sizing, multi-model Gemini for rate distribution.
- **Observability**: Request ID tracking, slow request detection (>1s), structured error responses.

---

## 5. Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.6.4 | Jun 17, 2026 | Documentation refresh aligned active docs to live code: 620 source files, 83 endpoint decorators, PostgreSQL/Neon async runtime, pgvector-enabled local compose, Redis optional cache posture, hydration/movement/nutrition/referral/promo endpoint inventory, and updated test scale. |
| 0.6.3 | Jun 13, 2026 | Single-owner logger and provider-neutral observability connector. Sentry direct imports isolated, cron/background boundaries own swallowed exception capture, safe scalar context allowlists documented. |
| 0.6.2 | May 15, 2026 | Configurable referral commissions (`REFERRAL_COMMISSIONS` env var, per-currency JSON). Custom unit-to-grams fix in nutrition calculation. BMR floor raised to 85% of standard daily; cutting deficit 500→300 kcal; clinical minimums 1200F/1500M. Email Universal Links (apple-app-site-association, /app-download). AsyncUnitOfWork concurrency guard (asyncio.Lock). Variable-length referral codes (3–15 chars). |
| 0.6.0 | Mar 14, 2026 | Nutrition accuracy (5-phase implementation): fiber-aware calories, food density conversion, macro validation, food reference evolution, meal decomposition. Custom macro targets per profile. Date of birth tracking. Adjusted daily target from weekly budget in suggestions. 3 new services, 3 new migrations (034-037), 28+ modified/new files. |
| 0.5.0 | Feb 3, 2026 | Historical documentation metric refresh for the then-current layer layout. Superseded by the June 2026 live-code snapshot above. |
| 0.4.9 | Jan 19, 2026 | Documentation refresh with updated dates. Verified CQRS patterns, domain services, and API endpoints against actual codebase. Weight-based macro calculation confirmed in TDEE service. |
| 0.4.7 | Jan 16, 2026 | Documentation refresh with scout-verified statistics (408 files, ~37K LOC). |
| 0.4.6 | Jan 9, 2026 | Phase 02: Language prompt integration (LANGUAGE_NAMES, language instructions, updated prompts). Phase 01: Meal suggestions multilingual support (7 languages, ISO 639-1 codes). |
| 0.4.5 | Jan 7, 2026 | Legacy vector-search migration work. Documentation split for modularity. |
| 0.4.4 | Jan 4, 2026 | Phase 03 Cleanup: Unified fitness goal enums to 3 canonical values. |
| 0.4.0 | Jan 3, 2026 | Phase 06: Session-based suggestions with 4h TTL. |
