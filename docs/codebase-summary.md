# MealTrack Backend - Codebase Summary

**Generated:** December 30, 2024
**Codebase Stats**: 59 Python source + test files, 138,200 tokens (main), 651,541 characters
**Language**: Python 3.11+
**Framework**: FastAPI 0.115.0+, SQLAlchemy 2.0
**Query Optimization**: N+1 prevention implemented with eager loading (Phase 02 complete)

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
├── src/                                 # Application source code
│   ├── api/                             # API Layer (HTTP endpoints)
│   ├── app/                             # Application Layer (CQRS)
│   ├── domain/                          # Domain Layer (Business logic)
│   └── infra/                           # Infrastructure Layer (Services)
├── tests/                               # Test suite
├── migrations/                          # Database migrations
├── docs/                                # Documentation
├── scripts/                             # Utility scripts
└── requirements.txt                     # Python dependencies
```

### Codebase Metrics

| Metric | Value |
|--------|-------|
| Total Python Files | 59 (source + tests) |
| Source Files (src/) | 40+ |
| Test Files | 20+ |
| Total Tokens | 138,200 |
| Total Characters | 651,541 |
| Average File Size | 11KB |
| Largest Files | Integration/unit tests (6K+ tokens) |

---

## Directory Layout

### Complete Directory Tree

```
src/
├── api/                                 # Presentation Layer
│   ├── main.py                          # FastAPI app initialization
│   ├── base_dependencies.py             # Shared dependencies
│   ├── routes/
│   │   └── v1/
│   │       ├── health.py                # Health check endpoints
│   │       ├── meals.py                 # Meal management routes
│   │       ├── chat.py                  # Chat endpoints
│   │       ├── chat_ws.py               # WebSocket chat
│   │       ├── meal_plans.py            # Meal planning routes
│   │       ├── user_profiles.py         # User profile routes
│   │       ├── users.py                 # User management routes
│   │       ├── foods.py                 # USDA food search routes
│   │       ├── notifications.py         # Push notification routes
│   │       ├── feature_flags.py         # Feature flag routes
│   │       ├── activities.py            # Activity tracking routes
│   │       ├── webhooks.py              # External webhook handlers
│   │       └── monitoring.py            # Monitoring endpoints
│   ├── schemas/
│   │   ├── request/                     # Request DTOs
│   │   ├── response/                    # Response DTOs
│   │   └── common/                      # Shared schemas
│   ├── mappers/                         # Entity -> Schema mappers
│   ├── converters/                      # Data conversion utilities
│   ├── dependencies/                    # FastAPI Depends providers
│   ├── middleware/                      # HTTP middleware
│   └── utils/                           # API utilities
│
├── app/                                 # Application Layer (CQRS)
│   ├── commands/                        # Command definitions
│   │   ├── meal/
│   │   ├── meal_plan/
│   │   ├── chat/
│   │   ├── user/
│   │   ├── daily_meal/
│   │   └── notification/
│   ├── queries/                         # Query definitions
│   │   ├── meal/
│   │   ├── meal_plan/
│   │   ├── chat/
│   │   ├── food/
│   │   ├── user/
│   │   ├── notification/
│   │   ├── activity/
│   │   └── tdee/
│   ├── events/                          # Domain event definitions
│   │   ├── meal/
│   │   ├── meal_plan/
│   │   ├── user/
│   │   ├── tdee/
│   │   └── daily_meal/
│   └── handlers/
│       ├── command_handlers/            # Command handler implementations
│       ├── query_handlers/              # Query handler implementations
│       └── event_handlers/              # Domain event subscribers
│
├── domain/                              # Domain Layer
│   ├── model/                           # Domain models (not ORM)
│   │   ├── ai/                          # AI-related models
│   │   ├── meal/
│   │   ├── meal_planning/
│   │   ├── nutrition/
│   │   ├── user/
│   │   ├── notification/
│   │   ├── chat/
│   │   └── conversation/
│   ├── services/                        # Domain services
│   │   ├── meal_service.py
│   │   ├── meal_plan_service.py
│   │   ├── user_service.py
│   │   ├── nutrition_service.py
│   │   ├── prompt_generation_service.py
│   │   └── ...
│   ├── strategies/                      # Strategy implementations
│   │   ├── meal_analysis_strategies.py
│   │   └── meal_edit_strategies.py
│   ├── ports/                           # Interface definitions (abstractions)
│   │   ├── repositories/
│   │   └── services/
│   ├── parsers/                         # Response parsing logic
│   ├── mappers/                         # Domain model mappers
│   ├── prompts/                         # AI prompt templates
│   └── constants/                       # Domain constants & enums
│
└── infra/                               # Infrastructure Layer
    ├── database/
    │   ├── config.py                    # Database connection setup
    │   ├── uow.py                       # Unit of Work pattern
    │   ├── models/                      # SQLAlchemy ORM models
    │   │   ├── base.py                  # Base model class
    │   │   ├── meal/
    │   │   ├── nutrition/
    │   │   ├── user/
    │   │   ├── meal_planning/
    │   │   ├── notification/
    │   │   ├── chat/
    │   │   ├── conversation/
    │   │   └── enums.py
    │   └── migration_manager.py         # Migration orchestration
    ├── repositories/                    # Data access layer
    │   ├── meal_repository.py
    │   ├── chat_repository.py
    │   ├── user_repository.py
    │   ├── meal_plan_repository.py
    │   ├── notification_repository.py
    │   └── ...
    ├── services/                        # External service adapters
    │   ├── ai/
    │   │   ├── gemini_service.py        # Google Gemini integration
    │   │   └── openai_chat_service.py   # OpenAI Chat integration
    │   ├── firebase_service.py          # Firebase auth & messaging
    │   ├── firebase_auth_service.py     # Firebase auth helpers
    │   ├── pinecone_service.py          # Vector DB integration
    │   ├── scheduled_notification_service.py
    │   └── usda_service.py              # USDA food database
    ├── adapters/                        # Third-party service adapters
    │   ├── cloudinary_adapter.py        # Image storage
    │   ├── storage_factory.py
    │   └── ...
    ├── cache/                           # Caching layer
    │   ├── redis_client.py              # Redis connection
    │   ├── cache_service.py             # Cache abstraction
    │   ├── cache_keys.py                # Cache key definitions
    │   ├── decorators.py                # Caching decorators
    │   └── metrics.py                   # Cache metrics
    ├── event_bus/                       # Event dispatcher
    │   └── event_bus.py                 # Event bus implementation
    ├── websocket/                       # WebSocket management
    │   └── connection_manager.py        # WebSocket connection pool
    ├── config/                          # Configuration management
    │   └── settings.py                  # Environment & settings
    └── mappers/                         # Infra -> Domain mappers
        └── ...
```

---

## Layer Responsibilities

### 1. API Layer (`src/api/`)

**Purpose**: Handle HTTP requests/responses and route them appropriately

**Key Components**:
- **Routes** (`routes/v1/`): 13 endpoint files handling REST operations
- **Schemas** (`schemas/`): 28+ Pydantic models for request/response validation
- **Mappers** (`mappers/`): Convert domain objects to API response schemas
- **Middleware**: CORS, authentication, error handling
- **Dependencies** (`dependencies/`): FastAPI `Depends()` providers for injection

**Example Routes**:
```python
# Meals: GET, POST (manual), PATCH (edit)
# Meal Plans: POST (generate), GET, PUT (replace)
# Chat: WebSocket, POST (message), GET (history)
# Users: POST (sync, onboarding), PUT (metrics)
# Foods: GET (search), GET (details)
# Notifications: POST (token), PUT (preferences)
# Feature Flags: GET (flag status), POST/PUT (admin)
```

**Responsibilities**:
- Validate incoming requests via Pydantic
- Call application commands/queries
- Serialize responses to JSON
- Handle HTTP status codes
- Implement CORS and authentication

### 2. Application Layer (`src/app/`)

**Purpose**: Implement CQRS pattern for decoupled command/query handling

**Key Components**:
- **Commands** (`commands/`): 19+ command definitions for state changes
- **Queries** (`queries/`): 15+ query definitions for reads
- **Command Handlers** (`handlers/command_handlers/`): 22+ implementations
- **Query Handlers** (`handlers/query_handlers/`): 18+ implementations
- **Events** (`events/`): Domain event definitions
- **Event Handlers** (`handlers/event_handlers/`): Event subscribers

**Command Examples**:
```
- UploadMealImageCommand
- CreateManualMealCommand
- EditMealCommand
- GenerateMealPlanCommand
- SendChatMessageCommand
- UpdateUserProfileCommand
- RegisterFCMTokenCommand
```

**Query Examples**:
```
- GetMealByIdQuery
- GetMealHistoryQuery
- GetMealPlanQuery
- SearchFoodsQuery
- GetChatThreadQuery
- GetUserProfileQuery
```

**Responsibilities**:
- Implement command handlers (side effects)
- Implement query handlers (reads)
- Publish domain events
- Coordinate with domain services
- Manage transactions via Unit of Work

### 3. Domain Layer (`src/domain/`)

**Purpose**: Encapsulate core business logic independent of frameworks

**Key Components**:
- **Models** (`model/`): 25+ domain entities (not ORM objects)
- **Services** (`services/`): 15+ domain services with business logic
- **Strategies** (`strategies/`): Pluggable algorithm implementations
- **Ports** (`ports/`): Interface definitions (abstractions)
- **Constants**: Enums and domain constants

**Domain Models**:
```
- Meal, MealItem, Nutrition
- MealPlan, MealPlanDay, PlannedMeal
- User, UserProfile, UserMetrics
- Food, FoodItem, NutrientData
- ChatThread, ChatMessage
- Notification, NotificationPreference
```

**Domain Services**:
```
- MealService: Meal creation, analysis, editing logic
- MealPlanService: Plan generation, optimization
- UserService: Profile management, TDEE calculation
- NutritionService: Nutrition aggregation, daily summaries
- PromptGenerationService: LLM prompt templating
```

**Strategies**:
```
- MealEditStrategies: Replace, remove, add food strategies
- MealAnalysisStrategies: Different AI analysis approaches
```

**Responsibilities**:
- Define domain entities and value objects
- Implement business logic as domain services
- Validate business rules
- Manage domain events
- Provide ports (interfaces) for infrastructure

### 4. Infrastructure Layer (`src/infra/`)

**Purpose**: Implement technical concerns and external integrations

**Key Components**:
- **Database** (`database/`): SQLAlchemy ORM models, migrations
- **Repositories** (`repositories/`): 7+ data access implementations
- **Services** (`services/`): External API adapters (Gemini, OpenAI, Firebase)
- **Adapters** (`adapters/`): Storage, cache, event implementations
- **Cache** (`cache/`): Redis caching layer
- **Event Bus** (`event_bus/`): Event dispatcher
- **WebSocket** (`websocket/`): Connection management

**ORM Models** (16+ SQLAlchemy models):
```
- Meal, MealImage, FoodItem, Nutrition
- MealPlan, MealPlanDay, PlannedMeal
- User, UserProfile, UserMetrics
- ChatThread, ChatMessage
- Conversation, ConversationMessage
- NotificationPreference, UserFCMToken
- FeatureFlag, Subscription
```

**Repositories**:
```
- MealRepository: Meal CRUD, history queries
- ChatRepository: Thread and message storage
- UserRepository: User and profile management
- MealPlanRepository: Plan storage and retrieval
- NotificationRepository: Preferences and tokens
```

**External Services**:
```
- GeminiService: Google Gemini vision API
- OpenAIChatService: GPT-4 chat integration
- FirebaseService: Auth and messaging
- PineconeService: Vector embeddings
- USDAService: Food database queries
- CloudinaryAdapter: Image storage
```

**Responsibilities**:
- Map domain models to/from ORM models
- Implement repository interfaces
- Manage database transactions
- Call external APIs
- Cache data for performance
- Handle persistence

---

## Key Files & Modules

### Critical Path Files

| File | Purpose | Size |
|------|---------|------|
| `src/api/main.py` | FastAPI app initialization, lifespan hooks | Core |
| `src/infra/database/config.py` | Database connection, engine setup | Critical |
| `src/infra/database/models/base.py` | Base SQLAlchemy model, timestamps | Critical |
| `src/infra/event_bus/event_bus.py` | CQRS event dispatcher | Core |
| `src/infra/services/ai/gemini_service.py` | Meal image analysis | Critical |
| `src/domain/services/meal_service.py` | Meal business logic | Large |
| `src/domain/services/meal_plan_service.py` | Meal plan generation | Large |
| `src/domain/services/prompt_generation_service.py` | LLM prompting | Large |

### Largest Files (by token count)

1. `tests/integration/test_timezone_aware_notifications.py` (6,202 tokens)
2. `tests/unit/test_chat_repository.py` (6,156 tokens)
3. `tests/unit/domain/test_meal_edit_strategies.py` (5,941 tokens)
4. `tests/unit/domain/services/test_meal_plan_service.py` (5,910 tokens)
5. `src/domain/services/prompt_generation_service.py` (5,381 tokens)

### Dependency Injection Points

**Main FastAPI Dependencies**:
```python
# In src/api/base_dependencies.py
- get_event_bus(): EventBus
- get_db_session(): AsyncSession
- get_cache_service(): CacheService
- get_firebase_auth(): FirebaseAuth
- get_current_user(): User (from Firebase token)
```

**Repository Factories**:
```python
- get_meal_repository(session)
- get_user_repository(session)
- get_chat_repository(session)
- get_meal_plan_repository(session)
```

---

## Module Dependencies

### Layer Dependencies (Clean Architecture)

```
API Layer
    ↓ depends on
Application Layer (CQRS)
    ↓ depends on
Domain Layer (Business Logic)
    ↓ depends on
Infrastructure Layer (External Services)
```

### Key Module Relationships

```
API Routes
    ↓ uses
Event Bus (Command/Query Dispatcher)
    ↓ routes to
Command/Query Handlers
    ↓ use
Domain Services + Repositories
    ↓ depend on
Repository Interfaces (Ports)
    ↓ implemented by
Infrastructure Repositories + Services
```

### External Dependencies (Top-level)

**Core Framework**:
```
fastapi==0.115.0+          # Web framework
pydantic==2.0+             # Data validation
sqlalchemy==2.0+           # ORM
```

**Database & Cache**:
```
mysql-connector-python     # MySQL driver
redis==7.0+                # Cache layer
alembic                    # Migrations
```

**AI/ML**:
```
langchain-google-genai     # Gemini integration
openai                     # GPT-4 API
pinecone-client           # Vector DB
```

**Firebase & Auth**:
```
firebase-admin            # Firebase SDK
python-jose               # JWT handling
```

**Testing**:
```
pytest>=7.0               # Test framework
pytest-asyncio            # Async test support
factory-boy               # Test data generation
```

---

## Entry Points

### Application Startup

```python
# Primary entry point
src/api/main.py::app

# Initialization sequence:
1. FastAPI(lifespan=lifespan) creates app
2. @lifespan yields startup code:
   - Initialize Firebase Admin SDK
   - Run database migrations
   - Start scheduled notification service
   - Initialize Redis cache
3. Include all routers
4. Mount static files (development)
```

### Running the Application

```bash
# Development
uvicorn src.api.main:app --reload

# Production
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Docker
docker run -p 8000:8000 mealtrack-backend:latest
```

### Database Migrations

```python
# Orchestrated by MigrationManager
src/infra/database/migration_manager.py

# Alembic migrations stored at:
migrations/versions/*.py

# Current version count: 10+ migrations
```

### Background Jobs

```python
# Scheduled notification service (runs in background)
src/infra/services/scheduled_notification_service.py

# Startup: initialize_scheduled_notification_service()
# Shutdown: await scheduled_service.stop()
```

---

## Data Models

### Core Domain Models (Non-ORM)

```python
# Meals
class Meal:
    meal_id: str
    user_id: str
    meal_items: List[MealItem]
    total_nutrition: Nutrition
    consumed_at: datetime
    status: MealStatus  # PROCESSING, READY, FAILED

# User
class User:
    user_id: str
    firebase_uid: str
    profile: UserProfile
    daily_goals: DailyGoals

# Meal Plan
class MealPlan:
    plan_id: str
    user_id: str
    days: List[MealPlanDay]
    preferences: DietaryPreferences

# Chat
class ChatThread:
    thread_id: str
    user_id: str
    messages: List[ChatMessage]
    context: Dict[str, Any]
```

### ORM Models (SQLAlchemy)

**Table Structure**:
```sql
-- Users
users (user_id, firebase_uid, created_at, updated_at)
user_profiles (profile_id, user_id, age, weight, height)

-- Meals
meals (meal_id, user_id, consumed_at, status)
meal_images (image_id, meal_id, image_url)
food_items (item_id, meal_id, food_id, quantity)
nutrition (nutrition_id, meal_id, calories, protein, carbs, fat)

-- Meal Planning
meal_plans (plan_id, user_id, start_date, end_date)
meal_plan_days (day_id, plan_id, day_number)
planned_meals (planned_meal_id, day_id, meal_id)

-- Chat
chat_threads (thread_id, user_id, created_at)
chat_messages (message_id, thread_id, role, content)

-- Notifications
notification_preferences (pref_id, user_id, email_enabled, push_enabled)
user_fcm_tokens (token_id, user_id, token, created_at)

-- Features
feature_flags (flag_id, flag_name, enabled, rollout_percentage)
```

---

## API Routes

### Route Organization (70+ endpoints)

```
/v1/
├── /health                          # Health checks
├── /meals                           # Meal management
│   ├── POST /image/analyze          # AI image analysis
│   ├── POST /manual                 # Manual entry
│   ├── GET /{id}                    # Get meal
│   ├── PATCH /{id}                  # Edit meal
│   └── GET /by-date                 # Query by date
├── /ingredients                     # New: Ingredient recognition
│   └── POST /recognize              # AI ingredient detection
├── /meal-suggestions                # New: Meal recommendations
│   ├── POST /generate               # Generate suggestions
│   └── POST /{id}/save              # Save suggestion
├── /meal-plans                      # Meal planning
│   ├── POST /generate               # Standard generation
│   ├── POST /generate/weekly-ingredient-based  # New: Ingredient-based
│   ├── GET /{id}
│   └── PUT /{id}/meals/{day}
├── /foods                           # Food database
│   ├── GET /search
│   └── GET /{id}
├── /chat                            # Chat endpoints
│   ├── POST /threads
│   ├── POST /threads/{id}/messages
│   ├── GET /threads/{id}/messages
│   └── WebSocket /ws/{thread_id}
├── /users                           # User management
│   ├── POST /sync
│   ├── POST /onboarding             # Updated: with pain points
│   └── POST /metrics/update
├── /user-profiles                   # Profile management
│   ├── GET /me
│   ├── PUT /me                      # Updated: with timezone
│   ├── GET /me/tdee
│   └── POST /me/tdee
├── /notifications                   # Push notifications
│   ├── POST /tokens                 # FCM token registration
│   ├── PUT /preferences
│   └── GET /preferences
├── /feature-flags                   # Feature management
│   └── GET /{flag}
├── /activities                      # Activity tracking
│   └── GET /
├── /webhooks                        # External webhooks
│   └── POST /revenucat              # Updated: RevenueCat webhooks
└── /monitoring                      # Monitoring/metrics
    └── GET /metrics
```

---

## Core Services

### Domain Services (Business Logic)

```
src/domain/services/
├── meal_service.py                  # Meal creation, editing, analysis
├── meal_plan_service.py             # Plan generation and optimization
├── user_service.py                  # User and profile management
├── nutrition_service.py             # Nutrition calculations and aggregations
├── prompt_generation_service.py     # LLM prompt generation
├── (and others for specific domains)
```

### Infrastructure Services (External Integration)

```
src/infra/services/
├── ai/
│   ├── gemini_service.py           # Google Gemini vision API
│   └── openai_chat_service.py      # OpenAI GPT-4 chat
├── firebase_service.py              # Firebase auth & messaging
├── firebase_auth_service.py         # Auth helper methods
├── pinecone_service.py              # Vector DB operations
├── scheduled_notification_service.py # Background notifications
└── usda_service.py                  # USDA food database
```

### Adapter Pattern (External Services)

```
src/infra/adapters/
├── cloudinary_adapter.py           # Image storage abstraction
├── storage_factory.py              # Factory for storage providers
└── (other adapters)
```

---

## Testing Organization

### Test Structure

```
tests/
├── conftest.py                      # Shared fixtures
├── factories/                       # Test data generators
│   └── (factory-boy factories)
├── unit/                            # Unit tests
│   ├── domain/
│   │   ├── services/
│   │   ├── test_meal_edit_strategies.py
│   │   └── ...
│   ├── test_chat_repository.py
│   └── ...
├── integration/                     # Integration tests
│   ├── test_meal_api.py
│   ├── test_timezone_aware_notifications.py
│   └── ...
└── fixtures/                        # Test data and mocks
    └── ...
```

### Test Coverage

| Component | Coverage | Status |
|-----------|----------|--------|
| Domain Services | 95%+ | Excellent |
| Repositories | 90%+ | Excellent |
| API Routes | 80%+ | Good |
| Infrastructure | 70%+ | Satisfactory |
| **Overall** | **70%+** | Meets minimum |

### Testing Strategy

1. **Unit Tests**: Fast, isolated, no database
2. **Integration Tests**: With real MySQL test database
3. **Database Isolation**: Transaction rollback per test
4. **Mock Factories**: factory-boy for test data generation
5. **External Service Mocks**: Mock AI/Firebase APIs

---

## Summary

The MealTrack Backend implements a robust 4-layer clean architecture with 59 core Python files organized by concern, totaling 138K tokens. The CQRS pattern in the application layer decouples API routes from business logic, while the domain layer encapsulates core business rules independently. The infrastructure layer handles all external integrations (Google Gemini 2.0, OpenAI GPT-4, Firebase, Pinecone, RevenueCat, Cloudinary, etc.), making the system highly testable and maintainable.

**Key Strengths**:
- Clear separation of concerns across 4 layers
- CQRS pattern for scalable command/query handling (40+ command/query handlers)
- Comprehensive test suite (70%+ coverage across 20+ test files)
- Event-driven architecture for loose coupling and reactive features
- Well-organized module structure by domain (13 core features)
- 70+ REST endpoints supporting diverse meal tracking workflows
- New features: ingredient recognition, meal suggestions, pain points tracking, timezone-aware notifications

**Recent Additions (v0.3.0)**:
- Ingredient recognition API (`/v1/ingredients/recognize`)
- Meal suggestions generation and saving
- User pain points collection during onboarding
- Timezone-aware notification scheduling
- RevenueCat subscription webhook integration
- 11 database migrations supporting all features

**Growth Points**:
- API response time optimization (p99 target <1s)
- Database query optimization for large datasets
- Integration test coverage for meal suggestion flows
- Performance profiling and benchmarking suite
- Comprehensive API documentation updates
- Distributed tracing and monitoring system
