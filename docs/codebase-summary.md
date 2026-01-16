# MealTrack Backend - Codebase Summary

**Generated:** January 16, 2026
**Codebase Stats**: 417 source files, ~37K LOC (src/), 681+ tests in 92 test files
**Source Files**: 417 Python files across 4 architecture layers
**Test Files**: 92 files with 681+ test cases, 70%+ coverage
**Language**: Python 3.11+
**Framework**: FastAPI 0.115+, SQLAlchemy 2.0
**Architecture**: 4-Layer Clean Architecture + CQRS + Event-Driven
**Event Bus**: PyMediator with singleton registry pattern
**Status**: Production-ready. Scout-verified metrics from comprehensive codebase analysis.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Directory Layout](#directory-layout)
3. [Layer Responsibilities](#layer-responsibilities)
4. [Key Files & Modules](#key-files--modules)
5. [Module Dependencies](#module-dependencies)
6. [Entry Points](#entry-points)
7. [Data Models](#data-models)
8. [API Routes](#api-routes)
9. [Core Services](#core-services)
10. [Testing Organization](#testing-organization)

---

## Project Structure

### High-Level Architecture

```
mealtrack_backend/
├── src/                                 # Application source code (417 files, ~37K LOC)
│   ├── api/                             # API Layer (74 files, ~8,241 LOC)
│   │   ├── routes/v1/                   # 12 route modules (50+ endpoints)
│   │   ├── schemas/                     # 34 Pydantic models (2,530 LOC)
│   │   ├── mappers/                     # 8 API ↔ Domain mappers (1,026 LOC)
│   │   ├── dependencies/                # FastAPI DI (auth, event_bus) (706 LOC)
│   │   ├── middleware/                  # 3-layer middleware (530 LOC)
│   │   └── utils/                       # API utilities (120 LOC)
│   ├── app/                             # Application Layer (136 files, ~5,968 LOC)
│   │   ├── commands/                    # 29 command definitions across 11 domains
│   │   ├── queries/                     # 23 query definitions
│   │   ├── events/                      # 10+ domain events
│   │   ├── handlers/                    # 40+ handlers total
│   │   │   ├── command_handlers/        # Command handlers
│   │   │   ├── query_handlers/          # Query handlers
│   │   │   └── event_handlers/          # Event handlers
│   │   └── services/chat/               # Application services (MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService)
│   ├── domain/                          # Domain Layer (130 files, ~14,079 LOC)
│   │   ├── model/                       # 30+ domain entities across 8 bounded contexts
│   │   │   ├── meal/                    # Meal aggregate with state machine
│   │   │   ├── nutrition/               # Nutrition bounded context
│   │   │   ├── user/                    # User bounded context
│   │   │   ├── meal_planning/           # Meal planning bounded context
│   │   │   ├── conversation/            # Conversation bounded context
│   │   │   ├── notification/            # Notification bounded context
│   │   │   ├── ai/                      # AI response models
│   │   │   └── chat/                    # Chat bounded context
│   │   ├── services/                    # 50+ domain services
│   │   ├── strategies/                  # 6 meal analysis strategies (Strategy Pattern)
│   │   ├── ports/                       # 17 port interfaces for dependency inversion
│   │   ├── prompts/                     # 4 AI prompt templates
│   │   ├── parsers/                     # GPT response parsers
│   │   └── constants/                   # Business constants
│   └── infra/                           # Infrastructure Layer (77 files, ~8,671 LOC)
│       ├── database/                    # SQLAlchemy + Alembic (connection pool: 20 + 10 overflow)
│       │   └── models/                  # 11 core database tables
│       ├── repositories/                # 10+ repository implementations with smart sync
│       ├── services/                    # External service adapters (Firebase, Pinecone)
│       ├── adapters/                    # Cloudinary, Vision AI, Meal Generation
│       ├── cache/                       # Redis cache-aside (50 connections, 1h default TTL)
│       ├── event_bus/                   # PyMediator with singleton registry and async execution
│       └── config/                      # Settings and configuration
├── tests/                               # Test suite (92 files, 681+ tests)
├── migrations/                          # Alembic migrations
├── docs/                                # Documentation
├── scripts/                             # Utility scripts
├── requirements.txt                     # Python dependencies
└── .env.example                         # Environment template
```

### Codebase Metrics (Updated Jan 16, 2026)

| Metric | Value |
|--------|-------|
| Total Source Files | 417 Python files |
| API Layer | 74 files, ~8,241 LOC |
| Application Layer | 136 files, ~5,968 LOC |
| Domain Layer | 130 files, ~14,079 LOC |
| Infrastructure Layer | 77 files, ~8,671 LOC |
| Total LOC (src/) | ~37,000 LOC |
| Test Files | 92 files |
| Total Test Cases | 681+ tests |
| Test Coverage | 70%+ maintained |
| API Endpoints | 50+ REST endpoints across 12 route modules |
| CQRS Commands | 29 commands across 11 domains |
| CQRS Queries | 23 query definitions |
| Domain Events | 10+ event definitions |
| Handlers | 40+ handlers with @handles decorator |
| Application Services | 3 (MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService) |
| Domain Services | 50+ service files |
| Bounded Contexts | 8 contexts (Meal, Nutrition, User, Planning, Conversation, Notification, AI, Chat) |
| Analysis Strategies | 6 strategies (basic, portion, ingredient, weight, user-context, combined) |
| Database Tables | 11 core tables |
| Repositories | 10+ with smart sync and eager loading |
| Port Interfaces | 17 port interfaces for dependency inversion |
| External Integrations | 7 (Gemini, Pinecone, Firebase, Cloudinary, RevenueCat, Redis, MySQL) |

---

## Directory Layout

### Complete Directory Tree

```
src/
├── api/                                 # Presentation Layer (74 files, ~8,241 LOC)
│   ├── main.py                          # FastAPI app initialization (228 lines)
│   ├── base_dependencies.py            # Service initialization
│   ├── exceptions.py                    # 7 custom exception types
│   ├── routes/v1/                       # 12 route modules with 50+ endpoints
│   │   ├── health.py                    # Health checks (3 endpoints)
│   │   ├── meals.py                     # Meal CRUD + analysis (6 endpoints)
│   │   ├── user_profiles.py            # Profile + TDEE (4 endpoints)
│   │   ├── users.py                     # User management
│   │   ├── foods.py                     # USDA food search
│   │   ├── meal_plans.py               # Weekly planning
│   │   ├── meal_suggestions.py         # AI suggestions
│   │   ├── activities.py               # Activity tracking
│   │   ├── notifications.py            # FCM tokens
│   │   ├── ingredients.py              # Ingredient recognition
│   │   ├── feature_flags.py            # Feature toggles
│   │   ├── webhooks.py                 # RevenueCat sync
│   │   ├── monitoring.py               # Observability
│   │   ├── chat/                       # AI chat (modular)
│   │   │   ├── thread_routes.py        # Thread management
│   │   │   └── message_routes.py       # Message operations
│   │   ├── chat_ws.py                  # WebSocket chat with ConnectionManager
│   │   └── daily_meals.py              # Daily suggestions
│   ├── schemas/                         # Pydantic DTOs (34 files, 2,530 LOC)
│   │   ├── request/                     # Request schemas
│   │   ├── response/                    # Response schemas
│   │   └── common/                      # Shared enums
│   ├── dependencies/                    # FastAPI DI (706 LOC)
│   │   ├── auth.py                      # Firebase JWT verification
│   │   └── event_bus.py                 # CQRS event bus wiring
│   ├── middleware/                      # HTTP middleware (530 LOC)
│   │   ├── dev_auth_bypass.py          # Dev user injection
│   │   ├── request_logger.py           # Request ID + timing
│   │   └── premium_check.py            # Subscription validation
│   ├── mappers/                         # API ↔ Domain (8 files, 1,026 LOC)
│   │   ├── base_mapper.py              # Abstract mapper pattern
│   │   ├── meal_mapper.py              # Meal transformations
│   │   ├── tdee_mapper.py              # TDEE calculations
│   │   ├── daily_meal_mapper.py
│   │   ├── meal_suggestion_mapper.py
│   │   ├── meal_plan_converters.py
│   │   └── chat_response_builder.py
│   └── utils/                           # Utilities (120 LOC)
│
├── app/                                 # Application Layer (136 files, ~5,967 LOC)
│   ├── commands/                        # 21 commands (596 LOC)
│   │   ├── meal/                        # Meal operations (4 commands)
│   │   ├── user/                        # User management (6 commands)
│   │   ├── meal_planning/              # Planning operations (3 commands)
│   │   ├── meal_suggestion/            # Suggestions (2 commands)
│   │   ├── chat/                        # Chat operations (3 commands)
│   │   ├── notification/               # Notifications (3 commands)
│   │   └── ingredient/                 # Ingredient recognition (1 command)
│   ├── queries/                         # 20 queries (359 LOC)
│   │   ├── meal/                        # Meal queries (2 queries)
│   │   ├── user/                        # User queries (5 queries)
│   │   ├── meal_planning/              # Planning queries (4 queries)
│   │   ├── daily_meal/                 # Daily meal queries (3 queries)
│   │   ├── food/                        # Food queries (2 queries)
│   │   ├── chat/                        # Chat queries (3 queries)
│   │   └── notification/               # Notification queries (1 query)
│   ├── events/                          # 11+ events (448 LOC)
│   │   ├── base.py                      # Event hierarchy (Command, Query, DomainEvent)
│   │   ├── meal/                        # Meal events (4 events)
│   │   ├── user/                        # User events (2 events)
│   │   ├── meal_planning/              # Planning events (3 events)
│   │   ├── daily_meal/                 # Daily meal events (1 event)
│   │   ├── tdee/                        # TDEE events (1 event)
│   │   └── chat/                        # Chat events (MessageSentEvent, ThreadCreated, etc.)
│   ├── handlers/                        # 49 handlers (4,008 LOC)
│   │   ├── command_handlers/           # 31 command handlers (~2,500 LOC)
│   │   ├── query_handlers/             # 18 query handlers (~1,000 LOC)
│   │   └── event_handlers/             # 1 event handler (126 LOC)
│   └── services/chat/                   # Application services (556 LOC)
│       ├── ai_response_coordinator.py   # Streaming AI responses
│       ├── chat_notification_service.py # FCM broadcasting
│       └── message_orchestration_service.py # Message flow coordination
│
├── domain/                              # Domain Layer (124 files, ~14,236 LOC)
│   ├── model/                           # Domain entities (44 files, 3,544 LOC)
│   │   ├── meal/                        # Meal, MealImage, Ingredient, MealStatus
│   │   ├── nutrition/                   # Nutrition, FoodItem, Macros, Micros, Food
│   │   ├── user/                        # Activity, TdeeRequest, TdeeResponse, MacroTargets
│   │   ├── meal_planning/              # MealPlan, PlannedMeal, DayPlan, UserPreferences
│   │   ├── conversation/               # Conversation, Message, ConversationState
│   │   ├── notification/               # UserFcmToken, NotificationPreferences, PushNotification
│   │   ├── ai/                          # GPTAnalysisResponse, GPTFoodItem, GPTResponseError
│   │   └── chat/                        # Thread, Message, ThreadStatus
│   ├── services/                        # 50 domain services (7,924 LOC)
│   │   ├── meal/                        # MealCoreService, MealFallbackService
│   │   ├── tdee_service.py             # TDEE calculation (auto-formula selection)
│   │   ├── nutrition_calculation_service.py # Nutrition aggregation
│   │   ├── meal_plan/                  # PlanOrchestrator, PlanGenerator, MealPlanValidator
│   │   ├── suggestion/                 # SuggestionService, SuggestionOrchestrationService
│   │   ├── conversation_service.py     # Conversation state management
│   │   ├── notification_service.py     # FCM push notifications
│   │   └── translation_service.py      # Multi-language support
│   ├── strategies/                      # 6 analysis strategies (725 LOC)
│   │   ├── meal_analysis_strategy.py   # Basic, Portion, Ingredient, Weight, UserContext, Combined
│   │   └── meal_edit_strategies.py     # Post-analysis editing strategies
│   ├── ports/                           # 15 port interfaces (997 LOC)
│   │   ├── repositories/               # Repository ports (7 ports)
│   │   └── services/                   # Service ports (8 ports: VisionAI, MealGeneration, etc.)
│   ├── prompts/                         # AI prompt templates (488 LOC)
│   │   ├── meal_suggestion_prompt.py   # 3 suggestions per request
│   │   ├── weekly_meal_plan_prompt.py  # 7-day plans
│   │   ├── daily_meal_plan_prompt.py   # Single day generation
│   │   └── unified_meal_plan_prompt.py # Combined prompts
│   ├── parsers/                         # GPT response parsers (184 LOC)
│   │   └── gpt_response_parser.py      # JSON extraction and validation
│   └── constants/                       # Business constants (185 LOC)
│       └── meal_constants.py           # MealDistribution, NutritionConstants, TDEEConstants
│
└── infra/                               # Infrastructure Layer (74 files, ~8,505 LOC)
    ├── database/                        # SQLAlchemy + Alembic
    │   ├── config.py                    # DB connection, pool sizing
    │   ├── models/                      # 11 main tables
    │   │   ├── base.py                  # PrimaryEntityMixin, SecondaryEntityMixin
    │   │   ├── user.py                  # User, UserProfile
    │   │   ├── subscription.py          # Subscription (RevenueCat cache)
    │   │   ├── meal.py                  # Meal, MealImage, Nutrition, FoodItem
    │   │   ├── meal_plan.py            # MealPlan, MealPlanDay, PlannedMeal
    │   │   ├── notification.py         # NotificationPreferences, UserFcmToken
    │   │   ├── chat.py                  # Thread, Message
    │   │   └── enums.py                 # MealStatusEnum, DietaryPreferenceEnum, etc.
    │   ├── migration_manager.py         # Alembic integration
    │   └── uow.py                       # Unit of Work pattern
    ├── repositories/                    # 10+ repositories
    │   ├── base.py                      # BaseRepository with CRUD
    │   ├── meal_repository.py          # Smart sync, eager loading
    │   ├── user_repository.py          # Firebase UID lookup, profile caching
    │   ├── notification_repository.py  # FCM token, preference operations
    │   └── ...                          # Subscription, MealPlan, Chat repositories
    ├── services/                        # External services
    │   ├── firebase_service.py         # FCM push notifications
    │   ├── pinecone_service.py         # Vector search (1024-dim)
    │   └── ai/                          # AI integrations
    │       └── gemini_chat_service.py  # Chat with streaming
    ├── adapters/                        # Service implementations
    │   ├── cloudinary_image_store.py   # Image storage (ImageStorePort)
    │   ├── vision_ai_service.py        # Meal analysis (VisionAIServicePort)
    │   └── meal_generation_service.py  # Multi-model Gemini (MealGenerationServicePort)
    ├── cache/                           # Redis caching
    │   ├── redis_client.py             # Async Redis with connection pool
    │   ├── cache_service.py            # Cache-aside pattern, JSON serialization
    │   ├── decorators.py               # Function-level caching
    │   └── metrics.py                  # Cache monitoring
    ├── event_bus/                       # CQRS event bus
    │   ├── event_bus.py                # EventBus interface
    │   └── pymediator_event_bus.py     # PyMediator implementation with singleton
    ├── config/                          # Configuration
    │   └── settings.py                  # Pydantic BaseSettings with .env
    └── websocket/                       # WebSocket support
        └── connection_manager.py        # Real-time connections
```

---

## Layer Responsibilities

### 1. API Layer (`src/api/`) - 74 files, ~8,241 LOC
**Purpose**: Handle HTTP requests/responses.
**Responsibilities**: Validate requests via Pydantic, dispatch commands/queries to event bus, serialize domain models to response DTOs, handle authentication/authorization.

**Key Components**:
- **12 Route Modules**: 50+ REST endpoints (health, meals, users, profiles, chat, notifications, meal plans, suggestions, activities, ingredients, webhooks, monitoring, feature flags, foods).
- **34 Pydantic Schemas**: Request/response DTOs with validation.
- **8 Mappers**: API ↔ Domain transformations (meal, TDEE, suggestions, chat).
- **3-Layer Middleware**: CORS, request logging (ID + timing), dev auth bypass.
- **Firebase JWT Auth**: Token verification with dev bypass for local development.
- **WebSocket Support**: ConnectionManager for real-time chat.

### 2. Application Layer (`src/app/`) - 136 files, ~5,968 LOC
**Purpose**: Implement CQRS pattern for decoupled operations.
**Responsibilities**: Execute commands/queries via handlers, publish domain events, coordinate transactions, orchestrate application services.

**Key Components**:
- **29 Commands**: Write operations across 11 domains (Chat, Meal, Daily Meal, Meal Plan, Meal Suggestion, User, Notification, Ingredient, TDEE, Activity, Food).
- **23 Queries**: Read operations (get meal, TDEE calculation, search foods, etc.).
- **10+ Domain Events**: Historical facts (meal analyzed, plan generated, message sent).
- **40+ Handlers**: Command, query, and event handlers with @handles decorator.
- **3 Application Services**: MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService.
- **UnitOfWork**: Transaction management pattern.

### 3. Domain Layer (`src/domain/`) - 130 files, ~14,079 LOC
**Purpose**: Encapsulate core business logic independent of external concerns.
**Responsibilities**: Domain models with business rules, domain services, port interfaces (dependency inversion), business constants, AI prompt templates.

**Key Components**:
- **8 Bounded Contexts**: Meal, Nutrition, User, Meal Planning, Conversation, Notification, AI, Chat.
- **30+ Domain Entities**: Rich models with validation and behavior (Meal aggregate with state machine, Nutrition, TdeeRequest, MealPlan, etc.).
- **50+ Domain Services**: TDEE calculation (BMR formulas: Mifflin-St Jeor, Katch-McArdle), nutrition aggregation, meal planning, suggestion generation, conversation management.
- **6 Analysis Strategies**: Basic, portion-aware, ingredient-aware, weight-aware, user-context-aware, combined (Strategy Pattern).
- **17 Port Interfaces**: Repository ports + service ports (VisionAI, MealGeneration, FoodData, ImageStore, etc.).
- **4 AI Prompt Templates**: Structured prompts for meal generation.

### 4. Infrastructure Layer (`src/infra/`) - 77 files, ~8,671 LOC
**Purpose**: Implement technical concerns and external integrations.
**Responsibilities**: Database persistence, external API adapters, caching, event bus implementation, configuration.

**Key Components**:
- **11 Database Tables**: User, UserProfile, Subscription, Meal, MealImage, Nutrition, FoodItem, MealPlan, NotificationPreferences, UserFcmToken, Thread, Message.
- **10+ Repositories**: Smart sync with diff-based updates, eager loading, request-scoped sessions.
- **External Services**: Firebase (FCM), Cloudinary (images), Gemini (AI with multi-model strategy), Pinecone (vector search with 1024-dim), RevenueCat (subscriptions).
- **Redis Cache**: Cache-aside pattern with graceful degradation, JSON serialization, 50 connections, 1h default TTL.
- **PyMediator Event Bus**: Singleton registry pattern, async event handling with @handles decorator.
- **MySQL Connection Pool**: 20 connections with 10 overflow capacity.

---

## Key Files & Modules

| File | Purpose |
|------|---------|
| `src/api/main.py` | FastAPI app initialization |
| `src/infra/database/config.py` | Database connection setup |
| `src/infra/services/ai/gemini_service.py` | Meal image analysis |
| `src/infra/services/pinecone_service.py` | Vector search (1024-dim vectors) |
| `src/domain/services/meal_service.py` | Meal business logic |
| `src/infra/event_bus/event_bus.py` | CQRS event dispatcher |

---

## Core Services

**PineconeNutritionService**:
- Pinecone Inference API integration with llama-text-embed-v2 (1024-dim embeddings).
- Semantic ingredient search with 0.35 similarity threshold.
- Nutrition scaling by portion with unit conversion.

**MealCoreService**:
- Manages meal lifecycle via state machine (PROCESSING → ANALYZING → READY/FAILED).
- Time-based meal type determination (breakfast 5-10:30, lunch 11-14:30, dinner 17-21, snack otherwise).
- Nutrition aggregation from food items with confidence scoring.

**TdeeCalculationService**:
- Auto-formula selection: Katch-McArdle (if body_fat%) or Mifflin-St Jeor.
- Activity multipliers (sedentary 1.2 → extra 1.9).
- Goal adjustments (CUT -500cal, BULK +300cal, RECOMP 0cal).
- Macro ratios by goal (BULK 30/45/25, CUT/RECOMP 35/40/25).

**SuggestionOrchestrationService**:
- Session-based suggestions with Redis 4h TTL.
- 7-language support (en, vi, es, fr, de, ja, zh) with ISO 639-1 codes.
- Portion multipliers (1-4x) and rejection feedback loop.

**MealGenerationService**:
- Multi-model Gemini for rate distribution (meal names, recipe primary/secondary, general).
- Structured output with Pydantic schema support.
- Token optimization based on content type (weekly 8000, suggestions 1500*count, single meal 1500).
- JSON cleaning (trailing commas, truncation recovery, structure closing).

---

## Testing Organization
- **Total Tests**: 681+ passing across 92 test files.
- **Coverage**: 70%+ overall, 100% on critical paths.
- **Organization**: `tests/unit/` (domain/app logic) and `tests/integration/` (API/infra).
- **Key Areas**: CQRS handlers, domain services, repositories, API endpoints, external service mocks.
- **Fixtures**: Shared fixtures for database, event bus, user profiles, meals.
- **Mocking**: External services mocked (Gemini, Pinecone, Firebase, Cloudinary, RevenueCat).
