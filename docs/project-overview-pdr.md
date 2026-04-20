# MealTrack Backend - Project Overview & Product Development Requirements

**Version:** 0.6.1
**Last Updated:** April 17, 2026
**Status:** Production-ready. 430 Python files, ~38.5K LOC across 4 layers. 681+ tests, 70%+ coverage. Latest: Sentry monitoring, meal discovery endpoint, notification deduplication, onboarding redesign (challenge_duration, training_types).

---

## Executive Summary

MealTrack Backend is a FastAPI-based service powering intelligent meal tracking and nutritional analysis. It implements Clean Architecture with CQRS pattern across 4 layers (430 files, ~38K LOC), integrating AI vision (Gemini 2.5 Flash with 6 analysis strategies) and chat (streaming responses via MessageOrchestrationService, AIResponseCoordinator) for real-time food recognition and personalized nutrition planning. The system handles 50+ REST endpoints across 12 route modules, supports 7 languages, and maintains 70%+ test coverage with 681+ tests. Latest stats: API (76 files, 8,605 LOC), App (140 files, 6,229 LOC), Domain (133 files, 14,556 LOC), Infra (80 files, 8,895 LOC).

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

### 2. RESTful API (50+ Endpoints across 12 Route Modules)
- **Meals**: image/analyze (POST), manual (POST), /{id} (GET/DELETE), ingredients (PUT), daily/macros (GET), streak, daily-breakdown.
- **User Profiles**: POST/GET/PUT profiles, TDEE calculation.
- **Meal Plans**: Weekly ingredient-based generation, meal retrieval by date.
- **Meal Suggestions**: Session-based with 4h TTL, portion multipliers (1-4x), rejection feedback, discovery endpoint (6 meals).
- **Chat**: Threads + Messages (REST + WebSocket), streaming AI responses via MessageOrchestrationService and AIResponseCoordinator.
- **Notifications**: FCM token management, deduplication (notification_sent_log), preferences with timezone-aware scheduling.
- **Foods**: USDA FDC search, barcode lookup with 6-step cascade (Nutritionix → Brave Search → AI fallback).
- **Webhooks**: RevenueCat subscription sync.
- **Activities**: Activity tracking and management.
- **Ingredients**: Ingredient recognition and analysis.
- **Monitoring**: Health checks, Sentry error/performance tracking, observability endpoints.
- **Feature Flags**: Feature toggle management.

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
- Pinecone Inference API with llama-text-embed-v2 (1024-dim embeddings).
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
- BMR floor (80% of standard daily) protects against dangerously low targets.

---

## 3. Technical Stack
- **Framework**: FastAPI 0.115+ (Python 3.11+)
- **Database**: MySQL 8.0 with SQLAlchemy 2.0 (request-scoped sessions), 13+ core tables
- **Cache**: Redis 7.0 with graceful degradation, JSON serialization
- **Vector DB**: Pinecone Inference API (1024-dim, llama-text-embed-v2)
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
- **Test Coverage**: 70%+ overall (681+ tests), 100% critical paths.
- **Maintainability**: <200 LOC per file, 4-Layer Clean Architecture with strict separation.
- **Security**: Firebase JWT verification, RevenueCat webhook auth, soft deletes, input sanitization.
- **Performance**: Request-scoped DB sessions, Redis caching with TTL, eager loading for queries.
- **Scalability**: Dynamic connection pool sizing, multi-model Gemini for rate distribution.
- **Observability**: Request ID tracking, slow request detection (>1s), structured error responses.

---

## 5. Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.6.0 | Mar 14, 2026 | Nutrition accuracy (5-phase implementation): fiber-aware calories, food density conversion, macro validation, food reference evolution, meal decomposition. Custom macro targets per profile. Date of birth tracking. Adjusted daily target from weekly budget in suggestions. 3 new services, 3 new migrations (034-037), 28+ modified/new files. |
| 0.5.0 | Feb 3, 2026 | Updated metrics across all layers: API (76 files, 8,605 LOC), App (140 files, 6,229 LOC), Domain (133 files, 14,556 LOC), Infra (80 files, 8,895 LOC). Total: 430 files, ~38K LOC. Fixed metric inconsistencies from previous documentation. |
| 0.4.9 | Jan 19, 2026 | Documentation refresh with updated dates. Verified CQRS patterns, domain services, and API endpoints against actual codebase. Weight-based macro calculation confirmed in TDEE service. |
| 0.4.7 | Jan 16, 2026 | Documentation refresh with scout-verified statistics (408 files, ~37K LOC). |
| 0.4.6 | Jan 9, 2026 | Phase 02: Language prompt integration (LANGUAGE_NAMES, language instructions, updated prompts). Phase 01: Meal suggestions multilingual support (7 languages, ISO 639-1 codes). |
| 0.4.5 | Jan 7, 2026 | Phase 05 Pinecone Migration (1024-dim). Documentation split for modularity. |
| 0.4.4 | Jan 4, 2026 | Phase 03 Cleanup: Unified fitness goal enums to 3 canonical values. |
| 0.4.0 | Jan 3, 2026 | Phase 06: Session-based suggestions with 4h TTL. |
