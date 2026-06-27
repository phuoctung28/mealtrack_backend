# MealTrack Backend - Project Overview & Product Development Requirements

**Version:** 0.6.6
**Last Updated:** June 27, 2026
**Status:** Production-ready current snapshot. 626 Python files, 53,696 LOC across 4 layers. 306 test files, 70%+ coverage target, and one known collection import error still needs cleanup. Latest: configurable referral commissions, BMR floor protection, custom unit normalization, email Universal Links, AsyncUnitOfWork concurrency guard, AI nutrition validation retries, and refreshed OpenAI-first provider routing.

---

## Executive Summary

MealTrack Backend is a FastAPI-based service powering intelligent meal tracking and nutritional analysis. It implements Clean Architecture with CQRS across 4 layers (626 files, 53.7K LOC), using provider-neutral AI routing with OpenAI primary and Cloudflare Workers AI fallback for meal analysis, text generation, and vision tasks. The system exposes 85 route decorators across 27 router registrations, supports 7 languages, and keeps the live codebase aligned with 306 test files. Latest stats: API (91 files, 10,624 LOC), App (207 files, 11,044 LOC), Domain (165 files, 16,152 LOC), Infra (154 files, 15,134 LOC).

---

## 1. Project Vision & Goals

### Vision Statement
Empower users to understand their nutrition through effortless, AI-driven tracking and personalized recommendations.

### Primary Goals
1. **Accuracy**: >90% food recognition accuracy through the current AI analysis pipeline.
2. **Efficiency**: Meal logging in < 30 seconds.
3. **Personalization**: Goal-based (CUT, BULK, RECOMP) nutritional targets.
4. **Performance**: API p95 < 500ms.

---

## 2. Core Features

### 1. AI-Powered Meal Analysis
- 6 analysis strategies: basic, portion-aware, ingredient-aware, weight-aware, user-context-aware, combined.
- Multi-food detection in single image with confidence scoring.
- OpenAI-first routing with Cloudflare Workers AI fallback for flexible context handling.
- Returns results in <3 seconds through state machine (PROCESSING → ANALYZING → READY/FAILED).

### 2. RESTful API (60+ Endpoints across 17 Route Modules)
- **Meals**: image/analyze, manual, parse-text, streak, weekly/daily-breakdown, weekly/budget, daily/macros, /{id} (GET/DELETE), ingredients (PUT).
- **User Profiles**: create, metrics (GET/POST), TDEE, custom-macros.
- **Users**: sync, Firebase UID lookups, metrics, timezone, language, delete.
- **Meal Suggestions**: generate (3/session, 4h TTL), discover (6 meals + images), recipes, save.
- **Saved Suggestions**: list, save, delete.
- **Foods**: USDA FDC search, details by FDC ID, barcode lookup (6-step cascade).
- **Ingredients**: image-based recognition.
- **TDEE**: preview calculation.
- **Weight Entries**: list, log, delete, sync.
- **Activities**: daily activities.
- **Notifications**: FCM token management, deduplication (notification_sent_log), preferences.
- **Referrals**: validate, apply, my-code, stats, payout.
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

### 5. Vector Search & Food Discovery
- PostgreSQL/pgvector-backed semantic search with 1024-dim embeddings.
- Semantic ingredient search with 0.35 similarity threshold.
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
- **Framework**: FastAPI 0.136.3 (Python 3.13.2)
- **Database**: PostgreSQL (Neon) with async SQLAlchemy 2.0 and pgvector-backed search
- **Cache**: Redis remains optional for cache-aside and AI-context caching; required state must be modeled separately
- **AI Services**: OpenAI primary with Cloudflare Workers AI fallback; provider routing is configured centrally

**AI Output Validation (2026-06)**: All meal-analysis and text-generation flows use canonical Pydantic contracts with bounded retry. Invalid AI output (over-limit quantities, empty foods) is rejected at the contract boundary with one automatic retry. The parser is a deterministic mapper, not a silent repair engine. Calories are always derived from backend macros, never from AI-reported kcal.
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
- **Test Coverage**: 70%+ overall target; collection currently has a known import error in the architecture test tree.
- **Maintainability**: <200 LOC per file, 4-Layer Clean Architecture with strict separation.
- **Security**: Firebase JWT verification, RevenueCat webhook auth, soft deletes, input sanitization.
- **Performance**: Request-scoped DB sessions, Redis caching with TTL, eager loading for queries.
- **Scalability**: Dynamic connection pool sizing, provider-neutral AI routing, and pgvector-backed search.
- **Observability**: Request ID tracking, slow request detection (>1s), structured error responses.

---

## 5. Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.6.6 | Jun 27, 2026 | Refreshed current snapshot metrics, aligned AI routing to OpenAI-first plus Cloudflare fallback, replaced Pinecone/Gemini-primary wording with the live search and provider stack, and updated testing/database counts to match the codebase. |
| 0.6.5 | Jun 13, 2026 | Added validation retry orchestration for structured AI nutrition output, with exactly one repair attempt for meal image scan and text parse flows, controlled `AIOutputValidationError` handling, preserved ingredient-recognition's unstructured contract, and kept calorie divergence checks anchored to backend-derived macro calories. |
| 0.6.4 | Jun 13, 2026 | Added canonical AI nutrition contracts for image and text flows, rejected impossible over-limit food quantities at validation time, preserved current text-parse macro compatibility, and removed silent invalid-food filtering from the legacy parser. |
| 0.6.2 | May 15, 2026 | Configurable referral commissions (`REFERRAL_COMMISSIONS` env var, per-currency JSON). Custom unit-to-grams fix in nutrition calculation. BMR floor raised to 85% of standard daily; cutting deficit 500→300 kcal; clinical minimums 1200F/1500M. Email Universal Links (apple-app-site-association, /app-download). AsyncUnitOfWork concurrency guard (asyncio.Lock). Variable-length referral codes (3–15 chars). |
| 0.6.0 | Mar 14, 2026 | Nutrition accuracy (5-phase implementation): fiber-aware calories, food density conversion, macro validation, food reference evolution, meal decomposition. Custom macro targets per profile. Date of birth tracking. Adjusted daily target from weekly budget in suggestions. 3 new services, 3 new migrations (034-037), 28+ modified/new files. |
| 0.5.0 | Feb 3, 2026 | Updated metrics across all layers: API (76 files, 8,605 LOC), App (140 files, 6,229 LOC), Domain (133 files, 14,556 LOC), Infra (80 files, 8,895 LOC). Total: 430 files, ~38K LOC. Fixed metric inconsistencies from previous documentation. |
| 0.4.9 | Jan 19, 2026 | Documentation refresh with updated dates. Verified CQRS patterns, domain services, and API endpoints against actual codebase. Weight-based macro calculation confirmed in TDEE service. |
| 0.4.7 | Jan 16, 2026 | Documentation refresh with scout-verified statistics (408 files, ~37K LOC). |
| 0.4.6 | Jan 9, 2026 | Phase 02: Language prompt integration (LANGUAGE_NAMES, language instructions, updated prompts). Phase 01: Meal suggestions multilingual support (7 languages, ISO 639-1 codes). |
| 0.4.5 | Jan 7, 2026 | Phase 05 Pinecone Migration (1024-dim). Documentation split for modularity. |
| 0.4.4 | Jan 4, 2026 | Phase 03 Cleanup: Unified fitness goal enums to 3 canonical values. |
| 0.4.0 | Jan 3, 2026 | Phase 06: Session-based suggestions with 4h TTL. |
