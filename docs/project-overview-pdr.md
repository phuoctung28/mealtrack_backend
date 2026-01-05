# MealTrack Backend - Project Overview & Product Development Requirements

**Last Updated:** January 4, 2026
**Version:** 0.4.4
**Status:** Active Development (Phase 01-03 Complete: Backend + Mobile Unification + Legacy Cleanup, Phase 06 Session-Based Meal Suggestions Active)

---

## Executive Summary

MealTrack Backend is a sophisticated FastAPI-based microservice that powers intelligent meal tracking and nutritional analysis with AI vision capabilities. The service combines advanced food recognition via Google Gemini AI with comprehensive nutritional data aggregation, enabling users to track meals effortlessly and receive personalized nutrition insights.

---

## Table of Contents

1. [Project Vision & Goals](#project-vision--goals)
2. [Target Users & Use Cases](#target-users--use-cases)
3. [Core Features](#core-features)
4. [Technical Requirements](#technical-requirements)
5. [Functional Requirements](#functional-requirements)
6. [Non-Functional Requirements](#non-functional-requirements)
7. [Architecture Overview](#architecture-overview)
8. [API Surface Area](#api-surface-area)
9. [Success Metrics](#success-metrics)
10. [Technology Stack](#technology-stack)
11. [Constraints & Assumptions](#constraints--assumptions)

---

## Project Vision & Goals

### Vision Statement
Empower users to understand their nutrition through intelligent, AI-driven meal tracking that requires minimal effort and maximum accuracy.

### Primary Goals

1. **Accurate Nutritional Analysis**: Leverage AI vision to identify foods with >90% accuracy
2. **Seamless User Experience**: Enable meal logging in under 30 seconds via image upload
3. **Personalized Insights**: Provide AI-driven meal planning and nutritional recommendations
4. **Scalable Infrastructure**: Support thousands of concurrent users with <500ms response times
5. **Data Privacy**: Maintain enterprise-grade security for sensitive health data

### Secondary Goals

1. Integrate with USDA Food Database for comprehensive nutrition data
2. Enable semantic search for food discovery via vector embeddings
3. Support meal planning with AI-generated meal recommendations
4. Provide push notifications for nutrition goals and hydration reminders
5. Support user preference settings and dietary goals

---

## Target Users & Use Cases

### Primary Users

1. **Health-Conscious Individuals** (40% of users)
   - Goal: Track calories, macros, and micronutrients
   - Pain point: Manual food logging is tedious
   - Solution: One-click image-based meal logging

2. **Fitness Enthusiasts** (35% of users)
   - Goal: Monitor protein intake and daily TDEE
   - Pain point: Inconsistent nutrient tracking
   - Solution: AI-powered meal analysis and personalized recommendations

3. **Dietary Managers** (25% of users)
   - Goal: Follow specific diets (keto, vegan, gluten-free)
   - Pain point: Need to identify compatible meals
   - Solution: Meal planning with dietary preference filters

### Use Cases

| Use Case | Actor | Flow |
|----------|-------|------|
| **Upload Meal Image** | Health-conscious user | Take photo → Upload → AI analysis → View results |
| **View Nutritional Details** | Fitness enthusiast | Select meal → View macros/micros → Compare to goals |
| **Get Meal Recommendation** | Dietary manager | Request plan → Specify preferences → Receive personalized meals |
| **Chat About Nutrition** | Any user | Ask question → AI responds with data-driven answer |
| **Track Daily Progress** | Any user | View dashboard → Check calories/macros → Adjust intake |

---

## Core Features

### 1. AI-Powered Meal Analysis (MVP)
**Status**: Active
**Description**: Analyze meal images using Google Gemini 2.0 vision to extract food items, quantities, and estimated nutrition.

**Capabilities**:
- Multi-food detection (identify multiple dishes in single image)
- Portion size estimation
- Cooking method recognition
- Nutritional composition extraction
- Confidence scoring for analysis reliability

**Acceptance Criteria**:
- [ ] Detects food items in images with >85% accuracy
- [ ] Estimates macro nutrients within ±15% of actual values
- [ ] Processes images in <3 seconds (p99)
- [ ] Handles 10K+ daily uploads

### 2. Meal Tracking & History
**Status**: Active
**Description**: Store, retrieve, and manage user meal history with nutritional summaries.

**Capabilities**:
- Create meals manually or via image analysis
- Edit meal details and portions
- View daily/weekly/monthly summaries
- Filter meals by date, food type, or nutrition targets
- Search meal history

**Acceptance Criteria**:
- [ ] Retrieve meal by ID in <100ms
- [ ] Query meal history with pagination in <200ms
- [ ] Support complex filters without performance degradation
- [ ] Store up to 10 years of meal history per user

### 3. Intelligent Meal Planning
**Status**: Active
**Description**: Generate personalized meal plans based on nutritional goals and preferences.

**Capabilities**:
- AI-powered meal plan generation
- Dietary preference support (vegan, keto, gluten-free, etc.)
- Caloric and macro targeting
- Meal replacement suggestions
- Variety optimization

**Acceptance Criteria**:
- [ ] Generate 7-day meal plan in <5 seconds
- [ ] Plan respects dietary restrictions 100%
- [ ] Meal variety score >0.8 (scale 0-1)
- [ ] Support 50+ dietary preferences

### 4. AI-Powered Chat & Nutrition Advice
**Status**: Active
**Description**: Enable users to ask nutrition questions and receive AI-driven responses with data backing.

**Capabilities**:
- Real-time chat with context awareness
- WebSocket support for streaming responses
- Nutrition data integration in responses
- Meal suggestion within chat context
- Chat history persistence

**Acceptance Criteria**:
- [ ] Response generation in <2 seconds (p95)
- [ ] WebSocket connections support 1000+ concurrent users
- [ ] Maintain conversation context across 20+ messages
- [ ] Hallucination rate <5%

### 5. User Profile & Goal Management
**Status**: Active
**Description**: Manage user profiles, dietary goals, and TDEE calculations.

**Capabilities**:
- User profile creation and updates
- Daily caloric goal setting
- Macro nutrient targets
- Activity level tracking
- TDEE (Total Daily Energy Expenditure) calculation
- Progress metrics tracking

**Acceptance Criteria**:
- [ ] TDEE calculation within ±10% of actual
- [ ] Support metric updates in real-time
- [ ] Recalculate nutrition analytics within 1 minute
- [ ] Track 20+ health metrics per user

### 6. Push Notifications
**Status**: Active
**Description**: Send timely notifications for nutrition goals, hydration, and meal planning.

**Capabilities**:
- Firebase Cloud Messaging integration
- Scheduled notifications
- Goal-based triggers
- User preference management
- Timezone-aware scheduling

**Acceptance Criteria**:
- [ ] 99.9% delivery rate to registered devices
- [ ] Notification delivery within 2 seconds of trigger
- [ ] Support 1 million+ FCM tokens
- [ ] User preferences honored 100%

### 7. Feature Flag Management
**Status**: Active
**Description**: Control feature rollout and A/B testing via dynamic feature flags.

**Capabilities**:
- Create/update/delete feature flags
- Gradual rollout support
- User segmentation
- Real-time flag evaluation
- Analytics integration

**Acceptance Criteria**:
- [ ] Flag evaluation <1ms latency
- [ ] Support 100+ concurrent flags
- [ ] Cache hit rate >95%
- [ ] Support user-level override

### 8. USDA Food Database Integration
**Status**: Active
**Description**: Access comprehensive USDA FoodData Central for accurate nutrition data.

**Capabilities**:
- FDC ID lookup
- Nutrition data retrieval
- Food description search
- Micronutrient data access
- Caching layer for performance

**Acceptance Criteria**:
- [ ] Support 300K+ food items
- [ ] Database queries return in <200ms (with cache)
- [ ] 99.5% uptime for food lookups
- [ ] Handle 100K+ daily food searches

### 9. Vector Search & Semantic Discovery
**Status**: Active
**Description**: Enable semantic search for food discovery using Pinecone vector embeddings.

**Capabilities**:
- Food embedding generation
- Semantic similarity search
- Food recommendation by similarity
- Query expansion for better results
- Multi-modal search (image + text)

**Acceptance Criteria**:
- [ ] Semantic search returns relevant results (MRR >0.8)
- [ ] Search queries processed in <500ms
- [ ] Support 300K+ food embeddings
- [ ] Multi-language search support

### 10. Ingredient Recognition
**Status**: Active
**Description**: AI-powered ingredient identification from meal images.

**Capabilities**:
- Identify individual ingredients from images
- Extract ingredient quantities
- Return ingredient-based suggestions
- Integration with meal planning

**Acceptance Criteria**:
- [ ] Identify ingredients with >85% accuracy
- [ ] Process images in <3 seconds (p99)
- [ ] Return structured ingredient data
- [ ] Support 1000+ daily recognition requests

### 11. Meal Suggestions (Session-Based - Phase 06)
**Status**: Active (Launched Jan 2026)
**Description**: AI-driven meal recommendations with session tracking and portion customization.

**Capabilities**:
- Generate 3 meal suggestions per session (cached in Redis)
- Session tracking with 4-hour TTL (Redis-backed)
- Accept suggestions with portion multiplier (1-4x)
- Reject suggestions with user feedback for model improvement
- Regenerate endpoint excludes previously shown suggestions
- Fallback mechanism with nutritionally-balanced meals
- GENERATION_TIMEOUT_SECONDS = 45s max per session
- Compatible with dietary preferences and daily goals
- 7 dedicated API endpoints for complete session lifecycle

**New Endpoints (Phase 06)**:
- `POST /v1/meal-suggestions/generate` - Create session with 3 suggestions
- `POST /v1/meal-suggestions/regenerate` - Get new batch excluding shown
- `GET /v1/meal-suggestions/{session_id}` - Retrieve session details
- `POST /v1/meal-suggestions/{suggestion_id}/accept` - Accept with portion (1-4x)
- `POST /v1/meal-suggestions/{suggestion_id}/reject` - Reject with optional feedback
- `DELETE /v1/meal-suggestions/{session_id}` - Discard session
- `GET /v1/meal-suggestions/{session_id}/history` - View session history

**Acceptance Criteria**:
- [ ] Generate suggestions in <10 seconds (current: 45s timeout, needs optimization)
- [x] Respect user dietary preferences 100%
- [x] Variety score >0.8 across suggestions
- [x] Support 50+ dietary restrictions
- [x] Session tracking with 4h TTL working
- [x] Fallback meals generation working
- [x] Portion multiplier (1-4x) calculation correct
- [x] Reject feedback logged for model improvement

### 12. User Pain Points Tracking
**Status**: Active
**Description**: Capture and track user health concerns during onboarding.

**Capabilities**:
- Collect pain points during signup
- Store pain points in user profile
- Use for personalized recommendations
- Track changes over time

**Acceptance Criteria**:
- [ ] Capture 5+ pain point categories
- [ ] Store pain points with timestamps
- [ ] Enable filtering by pain point
- [ ] Support pain point history tracking

### 13. Timezone-Aware Notifications
**Status**: Active
**Description**: Send notifications respecting user timezone preferences.

**Capabilities**:
- Capture user timezone during onboarding
- Schedule notifications in user's timezone
- Support timezone changes
- Prevent off-hours notifications

**Acceptance Criteria**:
- [ ] Store timezone per user
- [ ] Schedule notifications in user's timezone
- [ ] Honor quiet hours preferences
- [ ] Support 350+ timezone formats

---

## Technical Requirements

### Backend Framework
- **Framework**: FastAPI >= 0.115.0
- **Python**: 3.8+ (tested on 3.10, 3.13)
- **Async Runtime**: asyncio (built-in)

### Database & Storage
- **Primary Database**: MySQL 8.0+
- **ORM**: SQLAlchemy 2.0+
- **Migrations**: Alembic
- **Cache Layer**: Redis 7.0+
- **Cloud Storage**: Cloudinary or local file system

### External Integrations
- **AI Vision**: Google Gemini 2.5 Flash API
- **LLM Chat**: OpenAI GPT-4 API
- **Nutrition Data**: USDA FoodData Central API
- **Vector DB**: Pinecone
- **Authentication**: Firebase Admin SDK
- **Push Notifications**: Firebase Cloud Messaging
- **Image Storage**: Cloudinary CDN

### Development & Testing
- **Testing Framework**: pytest with async support
- **Test Coverage**: Minimum 70%
- **Mocking**: unittest.mock + factory-boy
- **Test Database**: MySQL transaction rollback isolation
- **CI/CD**: GitHub Actions
- **Code Quality**: ruff linting, black formatting, mypy type checking

### Deployment & DevOps
- **Containerization**: Docker multi-stage builds
- **Registry**: GitHub Container Registry (GHCR)
- **Orchestration**: Kubernetes (future)
- **Environment Management**: .env files via python-dotenv

---

## Functional Requirements

### FR-001: Meal Image Analysis
**Priority**: CRITICAL
**Description**: Process uploaded meal images using AI vision

```
Given: User uploads meal image
When: Image is received at /v1/meals/image/analyze
Then: System returns meal_id and processing_status
And: Background job analyzes image asynchronously
And: Meal is marked READY when analysis complete
```

**Sub-requirements**:
- FR-001.1: Support JPG, PNG, WebP formats (max 10MB)
- FR-001.2: Return analysis results within 30 seconds
- FR-001.3: Provide confidence scores for detected foods
- FR-001.4: Support retry mechanism for failed analyses

### FR-002: Manual Meal Entry
**Priority**: HIGH
**Description**: Allow users to manually log meals

```
Given: User wants to log meal without image
When: POST /v1/meals/manual with food details
Then: Meal is created with user-provided nutrition data
```

**Sub-requirements**:
- FR-002.1: Validate nutritional values (calories, macros)
- FR-002.2: Support portion size input (grams, cups, ounces)
- FR-002.3: Enable food search from USDA database

### FR-003: Meal Editing
**Priority**: HIGH
**Description**: Allow users to edit meal details post-analysis

```
Given: User wants to correct AI-detected food
When: PATCH /v1/meals/{id} with corrections
Then: Meal is updated with new nutrition data
And: Daily summaries are recalculated
```

**Sub-requirements**:
- FR-003.1: Support food replacement with new item
- FR-003.2: Support portion size adjustment
- FR-003.3: Support removal of detected foods
- FR-003.4: Support addition of missing foods

### FR-004: Meal Plan Generation
**Priority**: HIGH
**Description**: Generate AI-powered personalized meal plans

```
Given: User requests meal plan with preferences
When: POST /v1/meal-plans/generate
Then: Return 7-day meal plan
And: Plan respects dietary preferences and caloric goals
```

**Sub-requirements**:
- FR-004.1: Support dietary restrictions (vegan, keto, etc.)
- FR-004.2: Target specific macro ratios
- FR-004.3: Enable meal replacement in plan
- FR-004.4: Cache generated plans for performance

### FR-005: Chat Interface
**Priority**: MEDIUM
**Description**: Enable nutrition-focused chat with AI

```
Given: User initiates chat conversation
When: WebSocket connects to /v1/chat/ws
Then: User can send/receive messages in real-time
And: AI responses include nutrition data backing
```

**Sub-requirements**:
- FR-005.1: Maintain conversation context across messages
- FR-005.2: Support WebSocket streaming responses
- FR-005.3: Integrate user meal history in responses
- FR-005.4: Store chat history for future reference

### FR-006: User Profile Management
**Priority**: HIGH
**Description**: Manage user profiles and nutrition goals

```
Given: User creates account
When: POST /v1/users/onboarding with profile data
Then: User profile is created with goals
And: TDEE is calculated
And: Notification preferences initialized
```

**Sub-requirements**:
- FR-006.1: Support metric updates (weight, activity level)
- FR-006.2: Recalculate TDEE on metric changes
- FR-006.3: Store up to 20+ health metrics
- FR-006.4: Track metrics history for trending

### FR-007: Push Notifications
**Priority**: MEDIUM
**Description**: Send notifications for goals and reminders

```
Given: User reaches caloric goal
When: Daily check at configured time
Then: Push notification sent to device
And: Notification respects user preferences
```

**Sub-requirements**:
- FR-007.1: Support registration of FCM tokens
- FR-007.2: Allow users to manage notification types
- FR-007.3: Honor notification preferences per type
- FR-007.4: Support scheduled and event-triggered notifications

### FR-008: Feature Flag Management
**Priority**: MEDIUM
**Description**: Control feature rollout via flags

```
Given: Admin creates feature flag
When: POST /v1/feature-flags with flag definition
Then: Flag is available for evaluation
And: Can be toggled per user or globally
```

**Sub-requirements**:
- FR-008.1: Support percentage-based rollout (0-100%)
- FR-008.2: Cache flags for performance
- FR-008.3: Allow user-level overrides
- FR-008.4: Track flag evaluation metrics

---

## Non-Functional Requirements

### NFR-001: Performance
- **API Response Time**: p95 <500ms, p99 <1000ms
- **Image Analysis**: Complete within 30 seconds
- **Database Queries**: Complete within 200ms (95th percentile)
- **Cache Hit Rate**: Minimum 80% for frequently accessed data
- **Throughput**: Support 1000+ RPS

### NFR-002: Reliability
- **Availability**: 99.9% uptime
- **Error Rate**: <0.1% of requests
- **Data Loss**: Zero tolerance (atomic transactions)
- **Recovery Time**: <5 minutes for single-node failure

### NFR-003: Security
- **Authentication**: Firebase-based with JWT tokens
- **Authorization**: Role-based access control (RBAC)
- **Data Encryption**: TLS in transit, AES-256 at rest
- **SQL Injection**: Parameterized queries (SQLAlchemy)
- **CORS**: Configurable origins, no wildcard in production
- **Rate Limiting**: 100 requests/minute per user

### NFR-004: Scalability
- **Database**: Horizontal scaling via read replicas
- **Cache**: Redis cluster support
- **API**: Stateless design for horizontal scaling
- **Storage**: Cloud-native storage (Cloudinary)
- **Users**: Support 1M+ concurrent users

### NFR-005: Maintainability
- **Code Coverage**: Minimum 70%
- **Type Hints**: 100% coverage (mypy strict mode)
- **Documentation**: API docs via Swagger, README updated
- **Logging**: Structured logging for observability
- **Testing**: Unit + integration test suite

### NFR-006: Monitoring & Observability
- **Logging**: Structured JSON logs
- **Metrics**: Prometheus-compatible metrics
- **Tracing**: Correlation IDs for request tracking
- **Alerting**: Critical errors trigger alerts
- **Health Checks**: Liveness and readiness probes

---

## Architecture Overview

### 4-Layer Clean Architecture

```
┌─────────────────────────────────────────────┐
│         API Layer (Presentation)            │
│  - HTTP Routes, Schemas, Middleware         │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│      Application Layer (CQRS + Events)      │
│  - Commands, Queries, Event Handlers        │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│       Domain Layer (Business Logic)         │
│  - Entities, Services, Strategies           │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│     Infrastructure Layer (External Svcs)    │
│  - Repositories, Adapters, Database         │
└─────────────────────────────────────────────┘
```

### Design Patterns Employed

1. **Clean Architecture**: Clear separation of concerns across 4 layers
2. **CQRS (Command Query Responsibility Segregation)**: Separate read/write paths
3. **Event-Driven Architecture**: Decoupled components via event bus
4. **Repository Pattern**: Abstraction for data access
5. **Dependency Injection**: FastAPI `Depends()` for loose coupling
6. **Strategy Pattern**: Pluggable meal edit/analysis strategies
7. **Factory Pattern**: LLM provider auto-detection

---

## API Surface Area

### Base URL
```
https://api.mealtrack.app/v1
```

### API Endpoints (70+ Total)

#### Meals Management
- `POST /meals/image/analyze` - Analyze meal image with AI vision
- `GET /meals/{id}` - Get meal details
- `PATCH /meals/{id}` - Edit meal
- `POST /meals/manual` - Create meal manually
- `GET /meals/by-date` - Get meals by date range

#### Ingredients & Suggestions
- `POST /ingredients/recognize` - AI ingredient recognition from image
- `POST /meal-suggestions/generate` - Generate meal suggestions
- `POST /meal-suggestions/{id}/save` - Save suggestion as meal

#### Meal Planning
- `POST /meal-plans/generate` - Generate meal plan
- `POST /meal-plans/generate/weekly-ingredient-based` - Generate with ingredient options
- `GET /meal-plans/{id}` - Get meal plan
- `PUT /meal-plans/{id}/meals/{day}` - Replace meal in plan

#### Foods & Nutrition
- `GET /foods/search` - Search foods (USDA)
- `GET /foods/{id}` - Get food details

#### Chat
- `POST /chat/threads` - Create chat thread
- `POST /chat/threads/{id}/messages` - Send message
- `GET /chat/threads/{id}/messages` - Get thread history
- `WebSocket /chat/ws/{thread_id}` - WebSocket chat stream

#### Users
- `POST /users/sync` - Sync user from Firebase
- `POST /users/onboarding` - Complete onboarding with pain points
- `GET /user-profiles/me` - Get user profile
- `PUT /user-profiles/me` - Update user profile with timezone
- `GET /user-profiles/me/tdee` - Get TDEE calculation
- `POST /user-profiles/me/tdee` - Update TDEE calculation

#### Notifications
- `POST /notifications/tokens` - Register FCM token
- `PUT /notifications/preferences` - Update preferences
- `GET /notifications/preferences` - Get preferences

#### Feature Flags
- `GET /feature-flags/{flag}` - Get flag status
- `POST /feature-flags` - Create flag (admin)
- `PUT /feature-flags/{id}` - Update flag (admin)

#### Webhooks
- `POST /webhooks/revenucat` - RevenueCat subscription webhooks

---

## Success Metrics

### Business Metrics
| Metric | Target | Success Criteria |
|--------|--------|------------------|
| Daily Active Users | 10K+ | >8K DAU by Q2 |
| Meal Logging Rate | 2+ per user/day | 90% complete after 30 days |
| Repeat Usage Rate | 80% | Users return >3x per week |
| User Satisfaction | 4.5+/5 | App store rating target |

### Technical Metrics
| Metric | Target | SLO |
|--------|--------|-----|
| API Availability | 99.9% | <43 minutes downtime/month |
| Image Analysis Success | 95% | <5% fail rate |
| p95 Response Time | <500ms | <2s for complex queries |
| Cache Hit Rate | 80%+ | Cost reduction target |
| Error Rate | <0.1% | <1 error per 1000 requests |

### User Experience Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to Log Meal | <30s | From upload to complete |
| Image Analysis Accuracy | >85% | Macros within ±15% |
| Plan Generation Time | <5s | User wait time |
| Chat Response Latency | <2s | First token to user |

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.0+
- **ASGI Server**: Uvicorn
- **ORM**: SQLAlchemy 2.0
- **Database**: MySQL 8.0
- **Cache**: Redis 7.0
- **Async**: asyncio + aiohttp

### AI/ML Services
- **Vision AI**: Google Gemini 2.5 Flash (via google-genai SDK)
- **Chat/LLM**: OpenAI GPT-4 (via openai SDK)
- **Embeddings**: Pinecone (via pinecone SDK)
- **LangChain**: Orchestration for LLM chains

### Data & Integration
- **API Clients**: aiohttp, httpx
- **USDA Integration**: FoodData Central API
- **Image Storage**: Cloudinary SDK
- **Authentication**: Firebase Admin SDK
- **Push Notifications**: Firebase Cloud Messaging

### Testing & Quality
- **Testing**: pytest + pytest-asyncio
- **Test Data**: factory-boy
- **Mocking**: unittest.mock
- **Linting**: ruff
- **Formatting**: black
- **Type Checking**: mypy

### DevOps & Deployment
- **Containerization**: Docker
- **Registry**: GitHub Container Registry
- **CI/CD**: GitHub Actions
- **Environment**: python-dotenv
- **Migrations**: Alembic

---

## Constraints & Assumptions

### Technical Constraints

1. **Python 3.8+ Requirement**: Due to asyncio and type hints
2. **MySQL 8.0+**: Required for JSON functions and performance
3. **Redis Required**: Essential for caching and session management
4. **Google API Quota**: Limited to project quota limits
5. **Cloudinary Storage**: Free tier limits apply (50GB/month)

### Business Constraints

1. **GDPR Compliance**: Must handle user data deletion requests
2. **Food Data Licensing**: USDA data is public domain
3. **API Rate Limits**: Google/OpenAI have per-minute limits
4. **Cost Optimization**: AI API costs scale with usage

### Assumptions

1. **Users have valid Firebase authentication**
2. **USDA Food Database remains accessible and stable**
3. **Image quality sufficient for AI analysis (>300px)**
4. **Users have consistent internet connectivity**
5. **Firebase services maintain 99%+ availability**
6. **Third-party AI APIs remain available during requests**

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.4.4 | Jan 4, 2026 | Phase 03 Legacy Cleanup: Removed 13 ActivityGoalMapper aliases, simplified fitness goal enum to 3 canonical values (cut, bulk, recomp), updated 6 files with canonical response examples. All 681 tests passing. Greenfield deployment ready. |
| 0.4.0 | Jan 3, 2026 | Phase 06: Session-based meal suggestions with 4h TTL, 3 suggestions per session, portion multipliers (1-4x), rejection feedback, fallback mechanism (GENERATION_TIMEOUT_SECONDS=45s) |
| 0.3.0 | Dec 29, 2024 | Phase 05: Added ingredient recognition, meal suggestions, pain points tracking, timezone-aware notifications (13 core features) |
| 0.2.0 | Dec 2024 | Phase 04: Active development with 9 core features including chat system |
| 0.1.0 | Nov 2024 | Phase 01-03: Initial MVP with image analysis and meal tracking |

---

## References

- [API Documentation](../../../README.md#api-endpoints)
- [System Architecture](./system-architecture.md)
- [Event-Driven Architecture](./EVENT_DRIVEN_ARCHITECTURE.md)
- [Code Standards](./code-standards.md)
- [Testing Setup](./TESTING_SETUP.md)
