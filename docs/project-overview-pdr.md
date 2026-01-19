# MealTrack Backend - Project Overview & Product Development Requirements

**Version:** 0.4.9
**Last Updated:** January 19, 2026
**Status:** Production-ready. 417 source files, ~37K LOC across 4 layers. 681+ tests, 70%+ coverage.

---

## Executive Summary

MealTrack Backend is a FastAPI-based service powering intelligent meal tracking and nutritional analysis. It implements Clean Architecture with CQRS pattern across 4 layers (417 files, ~37K LOC), integrating AI vision (Gemini 2.5 Flash with 6 analysis strategies) and chat (streaming responses via MessageOrchestrationService) for real-time food recognition and personalized nutrition planning. The system handles 50+ REST endpoints across 12 route modules, supports 7 languages, and maintains 70%+ test coverage with 681+ tests.

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
- **Meals**: image/analyze (POST), manual (POST), /{id} (GET/DELETE), ingredients (PUT), daily/macros (GET).
- **User Profiles**: POST/GET/PUT profiles, TDEE calculation.
- **Meal Plans**: Weekly ingredient-based generation, meal retrieval by date.
- **Meal Suggestions**: Session-based with 4h TTL, portion multipliers (1-4x), rejection feedback.
- **Chat**: Threads + Messages (REST + WebSocket), streaming AI responses via MessageOrchestrationService and AIResponseCoordinator.
- **Notifications**: FCM token management, preferences with timezone-aware scheduling, ChatNotificationService for broadcasts.
- **Foods**: USDA FDC search and details.
- **Webhooks**: RevenueCat subscription sync.
- **Activities**: Activity tracking and management.
- **Ingredients**: Ingredient recognition and analysis.
- **Monitoring**: Health checks and observability endpoints.
- **Feature Flags**: Feature toggle management.

### 3. Session-Based Meal Suggestions
- Generates 3 personalized suggestions per session with Redis 4h TTL.
- Portion multipliers (1-4x) and rejection feedback loop.
- Multi-language support (7 languages: en, vi, es, fr, de, ja, zh) with fallback.
- Language-aware prompt generation with injected instructions.

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

---

## 3. Technical Stack
- **Framework**: FastAPI 0.115+ (Python 3.11+)
- **Database**: MySQL 8.0 with SQLAlchemy 2.0 (request-scoped sessions), 11 core tables
- **Cache**: Redis 7.0 with graceful degradation, JSON serialization
- **Vector DB**: Pinecone Inference API (1024-dim, llama-text-embed-v2)
- **AI Services**: Google Gemini 2.5 Flash (multi-model for rate distribution)
- **Storage**: Cloudinary (image storage with folder organization)
- **Auth**: Firebase JWT with development bypass middleware
- **Event Bus**: PyMediator with singleton registry pattern
- **Notifications**: Firebase Cloud Messaging (FCM) with platform-specific configs
- **Subscriptions**: RevenueCat webhook integration

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
| 0.4.9 | Jan 19, 2026 | Documentation refresh with updated dates. Verified CQRS patterns, domain services, and API endpoints against actual codebase. Weight-based macro calculation confirmed in TDEE service. |
| 0.4.8 | Jan 16, 2026 | Updated documentation with accurate scout-verified statistics (417 files, ~37K LOC). Added WebSocket chat details, application services (MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService), and EventBus singleton pattern. Updated CQRS counts: 29 commands, 23 queries, 10+ events, 40+ handlers. |
| 0.4.7 | Jan 16, 2026 | Documentation refresh with scout-verified statistics (408 files, ~37K LOC). |
| 0.4.6 | Jan 9, 2026 | Phase 02: Language prompt integration (LANGUAGE_NAMES, language instructions, updated prompts). Phase 01: Meal suggestions multilingual support (7 languages, ISO 639-1 codes). |
| 0.4.5 | Jan 7, 2026 | Phase 05 Pinecone Migration (1024-dim). Documentation split for modularity. |
| 0.4.4 | Jan 4, 2026 | Phase 03 Cleanup: Unified fitness goal enums to 3 canonical values. |
| 0.4.0 | Jan 3, 2026 | Phase 06: Session-based suggestions with 4h TTL. |
