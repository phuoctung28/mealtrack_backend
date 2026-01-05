# MealTrack Backend - Codebase Summary

**Generated:** January 4, 2026
**Codebase Stats**: 515 total files, 474,298 tokens, 2.2M+ characters
**Source Files**: ~145 Python files (src/)
**Test Files**: 57 files with 681 test cases
**Language**: Python 3.11+
**Framework**: FastAPI 0.115.0+, SQLAlchemy 2.0
**Architecture**: 4-Layer Clean Architecture + CQRS + Event-Driven
**Status**: Phase 03 Backend Legacy Cleanup Complete + Phase 06 Session-Based Meal Suggestions Active (681+ tests passing, 70%+ code coverage)

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
├── src/                                 # Application source code (145 files)
│   ├── api/                             # API Layer (HTTP endpoints)
│   │   ├── routes/v1/                   # 13+ endpoint files (70+ routes)
│   │   ├── schemas/                     # 28+ Pydantic models
│   │   ├── mappers/                     # Domain to API conversion
│   │   ├── dependencies/                # FastAPI DI providers
│   │   ├── middleware/                  # HTTP middleware
│   │   └── utils/                       # API utilities
│   ├── app/                             # Application Layer (CQRS)
│   │   ├── commands/                    # 34+ command definitions
│   │   ├── queries/                     # 30+ query definitions
│   │   ├── events/                      # 18 domain events
│   │   └── handlers/                    # 54+ total handlers
│   ├── domain/                          # Domain Layer (Business logic)
│   │   ├── model/                       # 25+ domain entities
│   │   ├── services/                    # 36 service files (refactored)
│   │   ├── strategies/                  # Strategy implementations
│   │   ├── ports/                       # Interface definitions
│   │   └── prompts/                     # AI prompt templates
│   └── infra/                           # Infrastructure Layer
│       ├── database/                    # SQLAlchemy + Alembic (11 migrations)
│       ├── repositories/                # 7+ data access implementations
│       ├── services/                    # External service adapters
│       ├── cache/                       # Redis caching
│       ├── event_bus/                   # Event dispatcher
│       └── adapters/                    # Storage & integrations
├── tests/                               # Test suite (57 files, 681 tests)
├── migrations/                          # Database migrations (11 versions)
├── docs/                                # Documentation (5+ files)
├── scripts/                             # Utility scripts
├── requirements.txt                     # Python dependencies
└── .env.example                         # Environment template
```

### Codebase Metrics (Updated Jan 2026)

| Metric | Value |
|--------|-------|
| Total Files | 515 (73 Python source + tests, 442 other) |
| Source Files (src/) | ~145 files |
| Test Files | 57 files |
| Total Test Cases | 681 tests |
| Total Tokens | 473,592 |
| Total Characters | 2.2M+ |
| Lines of Code (src/) | 33,308 LOC |
| API Endpoints | 70+ REST endpoints |
| CQRS Commands | 34+ command definitions |
| CQRS Queries | 30+ query definitions |
| Event Handlers | 54+ total (43 command, 11 query) |
| Database Tables | 27 tables across 11 migrations |
| Domain Services | 36 files (refactored from 4 monolithic) |
| Code Coverage | 70%+ maintained |

### Phase 03: Complete Refactoring & Legacy Cleanup (Completed Jan 4, 2026)

**Stage 1 (Dec 31, 2024): Service Refactoring**

4 large backend files refactored into 13 specialized components:

| Original File | LOC (Before) | LOC (After) | Reduction | Components |
|---|---|---|---|---|
| meal_plan_orchestration_service.py | 534 | 155 | -71% | 4 modules |
| daily_meal_suggestion_service.py | 525 | 195 | -63% | 3 modules |
| conversation_service.py | 476 | 63 | -87% | 3 modules |
| notification_repository.py | 428 | 138 | -68% | 3 modules |
| **TOTAL** | **1,963** | **551** | **-72%** | **13 components** |

**Stage 2 (Jan 4, 2026): Legacy Cleanup**

Removed backward compatibility aliases for greenfield deployment:

| Category | Removed | Impact |
|----------|---------|--------|
| ActivityGoalMapper aliases | 13 mappings → 3 canonical | Simplified enum handling |
| API schemas | maintenance/cutting/bulking refs | Canonical 3-value set only |
| Response examples | 5 updated | Consistent canonical values |
| Test fixtures | Updated to canonical values | All 681 tests passing |

**Phase 03 Achievement Summary**:
- ✅ All 681 tests passing (100%)
- ✅ Zero breaking changes to API interface
- ✅ 72% LOC reduction (1,963 → 551 LOC)
- ✅ 13 new specialized components
- ✅ Legacy aliases removed (greenfield ready)
- ✅ Canonical 3-value fitness goal enum throughout system

---

## Directory Layout

### Complete Directory Tree

```
src/
├── api/                                 # Presentation Layer (72 files, 8,278 LOC)
│   ├── main.py                          # FastAPI app initialization
│   ├── base_dependencies.py             # Shared dependencies
│   ├── routes/v1/                       # 13+ route files
│   │   ├── health.py
│   │   ├── meals.py                     # 6 endpoints
│   │   ├── meal_suggestions.py          # 7 endpoints (Phase 06 NEW)
│   │   ├── meal_plans.py                # 3 endpoints
│   │   ├── chat/                        # Chat endpoints
│   │   ├── chat_ws.py                   # WebSocket chat
│   │   ├── user_profiles.py             # 3 endpoints
│   │   ├── users.py                     # 5 endpoints
│   │   ├── foods.py                     # 2 endpoints
│   │   ├── notifications.py             # 3 endpoints
│   │   ├── ingredients.py               # 2 endpoints (NEW v0.3)
│   │   ├── feature_flags.py             # 3 endpoints
│   │   ├── webhooks.py                  # RevenueCat
│   │   ├── monitoring.py                # 1 endpoint
│   │   ├── activities.py                # 1 endpoint
│   │   └── daily_meals.py               # 1 endpoint
│   ├── schemas/                         # 28+ Pydantic models
│   │   ├── request/                     # Request DTOs (13+ files)
│   │   └── response/                    # Response DTOs (10+ files)
│   ├── mappers/                         # Entity -> Schema converters
│   ├── dependencies/                    # FastAPI Depends providers
│   ├── middleware/                      # Auth bypass, premium check
│   └── utils/                           # File validation, etc
│
├── app/                                 # Application Layer (145 files, 6,340 LOC - CQRS)
│   ├── commands/                        # 34+ command definitions
│   │   ├── meal/                        # Meal commands (5+)
│   │   ├── meal_plan/                   # Meal planning (3+)
│   │   ├── chat/                        # Chat (3+)
│   │   ├── user/                        # User (3+)
│   │   ├── daily_meal/                  # Daily suggestions (2+)
│   │   ├── notification/                # Notifications (2+)
│   │   ├── ingredient/                  # Ingredients (1+)
│   │   └── meal_suggestion/             # Suggestions (NEW)
│   ├── queries/                         # 30+ query definitions
│   │   ├── meal/
│   │   ├── meal_plan/
│   │   ├── chat/
│   │   ├── food/
│   │   ├── user/
│   │   ├── notification/
│   │   ├── activity/
│   │   ├── tdee/
│   │   └── ingredient/
│   ├── events/                          # Domain event definitions
│   │   ├── meal/
│   │   ├── meal_plan/
│   │   ├── user/
│   │   ├── tdee/
│   │   └── daily_meal/
│   └── handlers/                        # 54+ total implementations
│       ├── command_handlers/            # 43+ implementations
│       ├── query_handlers/              # 11+ implementations
│       └── event_handlers/              # Event subscribers
│
├── domain/                              # Domain Layer (107 files, 11,282 LOC)
│   ├── model/                           # 25+ domain entities
│   │   ├── ai/                          # AI-related models
│   │   ├── meal/                        # Meal entities
│   │   ├── meal_planning/               # Planning models
│   │   ├── nutrition/                   # Nutrition models
│   │   ├── user/                        # User models
│   │   ├── notification/                # Notification models
│   │   ├── chat/                        # Chat models
│   │   └── conversation/                # Conversation models
│   ├── services/                        # 36 service files (refactored)
│   │   ├── meal_service.py              # Core meal operations
│   │   ├── meal_plan/                   # 4 components (refactored)
│   │   │   ├── meal_plan_validator.py
│   │   │   ├── meal_plan_generator.py
│   │   │   ├── meal_plan_formatter.py
│   │   │   └── request_builder.py
│   │   ├── meal_suggestion/             # 3 components (refactored)
│   │   │   ├── json_extractor.py
│   │   │   ├── suggestion_fallback_provider.py
│   │   │   └── suggestion_prompt_builder.py
│   │   ├── conversation/                # 3 components (refactored)
│   │   │   ├── conversation_parser.py
│   │   │   ├── conversation_formatter.py
│   │   │   └── conversation_handler.py
│   │   ├── meal_plan_service.py
│   │   ├── suggestion_orchestration_service.py   # Phase 06 NEW
│   │   ├── user_service.py
│   │   ├── nutrition_service.py
│   │   ├── prompt_generation_service.py
│   │   ├── tdee_service.py
│   │   └── (10+ other services)
│   ├── strategies/                      # Strategy implementations
│   │   ├── meal_analysis_strategies.py  # 5 concrete strategies
│   │   └── meal_edit_strategies.py      # Replace, remove, add
│   ├── ports/                           # Interface definitions
│   │   ├── repositories/
│   │   └── services/
│   ├── parsers/                         # Response parsing
│   ├── mappers/                         # Domain model mappers
│   ├── prompts/                         # AI prompt templates
│   └── constants/                       # Enums & domain constants
│
└── infra/                               # Infrastructure Layer (76 files, 7,408 LOC)
    ├── database/                        # SQLAlchemy + Alembic
    │   ├── config.py                    # Database connection
    │   ├── uow.py                       # Unit of Work pattern
    │   ├── models/                      # 16+ SQLAlchemy models
    │   │   ├── meal/
    │   │   ├── nutrition/
    │   │   ├── user/
    │   │   ├── meal_planning/
    │   │   ├── notification/
    │   │   ├── chat/
    │   │   ├── conversation/
    │   │   └── enums.py
    │   └── migration_manager.py
    ├── repositories/                    # 7+ data access implementations
    │   ├── meal_repository.py
    │   ├── chat_repository.py
    │   ├── user_repository.py
    │   ├── meal_plan_repository.py
    │   ├── notification/                # 3 components (refactored)
    │   │   ├── fcm_token_operations.py
    │   │   ├── notification_preferences_operations.py
    │   │   └── reminder_query_builder.py
    │   └── (others)
    ├── services/                        # External service adapters
    │   ├── ai/
    │   │   ├── gemini_service.py        # Google Gemini 2.5 Flash
    │   │   └── openai_chat_service.py   # OpenAI GPT-4
    │   ├── firebase_service.py          # Auth & messaging
    │   ├── firebase_auth_service.py     # Auth helpers
    │   ├── pinecone_service.py          # Vector DB
    │   ├── scheduled_notification_service.py
    │   └── usda_service.py              # Food database
    ├── adapters/                        # Third-party adapters
    │   ├── cloudinary_adapter.py        # Image storage
    │   ├── storage_factory.py
    │   └── (others)
    ├── cache/                           # Redis caching
    │   ├── redis_client.py
    │   ├── cache_service.py
    │   ├── cache_keys.py
    │   ├── decorators.py
    │   └── metrics.py
    ├── event_bus/                       # Event dispatcher
    │   └── event_bus.py                 # PyMediator implementation
    ├── websocket/                       # WebSocket management
    │   └── connection_manager.py
    ├── config/                          # Configuration
    │   └── settings.py
    └── mappers/                         # Infra -> Domain converters
```

---

## Layer Responsibilities

### 1. API Layer (`src/api/`) - 72 files, 8,278 LOC

**Purpose**: Handle HTTP requests/responses

**Components**:
- **Routes** (13+ files): 70+ REST endpoints
- **Schemas** (28+ Pydantic models): Request/response validation
- **Mappers**: Domain to API conversion
- **Middleware**: CORS, auth, error handling
- **Dependencies**: FastAPI `Depends()` providers

**Responsibilities**:
- Validate incoming requests
- Call application commands/queries
- Serialize responses to JSON
- Handle HTTP status codes
- Implement authentication

### 2. Application Layer (`src/app/`) - 145 files, 6,340 LOC - CQRS

**Purpose**: Implement CQRS pattern for decoupled operations

**Components**:
- **Commands** (34+): State change operations
- **Queries** (30+): Read operations
- **Command Handlers** (43+): Command implementations
- **Query Handlers** (11+): Query implementations
- **Events** (18): Domain events
- **Event Handlers**: Event subscribers

**Responsibilities**:
- Implement command handlers (side effects)
- Implement query handlers (reads)
- Publish domain events
- Coordinate with domain services
- Manage transactions

### 3. Domain Layer (`src/domain/`) - 107 files, 11,282 LOC

**Purpose**: Encapsulate core business logic

**Components**:
- **Models** (25+): Domain entities (not ORM)
- **Services** (36 files): Business logic
- **Strategies** (2 files): Pluggable algorithms
- **Ports**: Interface definitions
- **Constants**: Enums and domain constants

**Responsibilities**:
- Define domain entities
- Implement business logic
- Validate business rules
- Manage domain events
- Provide port interfaces

### 4. Infrastructure Layer (`src/infra/`) - 76 files, 7,408 LOC

**Purpose**: Implement technical concerns and integrations

**Components**:
- **Database**: SQLAlchemy ORM, Alembic migrations (11 versions)
- **Repositories** (7+): Data access implementations
- **Services**: External API adapters
- **Cache**: Redis caching layer
- **Event Bus**: Event dispatcher
- **Adapters**: Storage and integrations

**Responsibilities**:
- Map domain to ORM models
- Implement repository interfaces
- Manage database transactions
- Call external APIs
- Cache data

---

## Key Files & Modules

### Critical Path Files

| File | Purpose | Impact |
|------|---------|--------|
| `src/api/main.py` | FastAPI app initialization | Core |
| `src/infra/database/config.py` | Database connection setup | Critical |
| `src/infra/services/ai/gemini_service.py` | Meal image analysis | Critical |
| `src/domain/services/meal_service.py` | Meal business logic | Core |
| `src/domain/services/suggestion_orchestration_service.py` | Session-based suggestions (Phase 06) | Core |
| `src/infra/event_bus/event_bus.py` | CQRS event dispatcher | Core |

### Largest Components (by LOC)

1. `src/domain/services/prompt_generation_service.py` (5,381 tokens)
2. `tests/unit/domain/services/test_meal_plan_service.py` (5,910 tokens)
3. `tests/unit/domain/test_meal_edit_strategies.py` (5,941 tokens)
4. `tests/integration/test_timezone_aware_notifications.py` (6,202 tokens)
5. `tests/unit/test_chat_repository.py` (6,156 tokens)

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
- fastapi==0.115.0+
- pydantic==2.0+
- sqlalchemy==2.0+

**Database & Cache**:
- mysql-connector-python
- redis==7.0+
- alembic

**AI/ML**:
- langchain-google-genai
- openai
- pinecone-client

**Firebase & Auth**:
- firebase-admin
- python-jose

**Testing**:
- pytest>=7.0
- pytest-asyncio
- factory-boy

---

## Entry Points

### Application Startup

```python
# Primary entry point: src/api/main.py::app
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

# Meal Suggestions (Phase 06 NEW)
class MealSuggestion:
    suggestion_id: str
    session_id: str
    meal_name: str
    macro_estimate: MacroEstimate
    portion_type: MealPortionType

class SuggestionSession:
    session_id: str
    user_id: str
    suggestions: List[MealSuggestion]
    created_at: datetime

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

### ORM Models (SQLAlchemy - 27 tables)

**Users**:
- users, user_profiles, user_metrics

**Meals**:
- meals, meal_images, food_items, nutrition

**Meal Planning**:
- meal_plans, meal_plan_days, planned_meals

**Suggestions** (NEW v0.3):
- meal_suggestions, suggestion_sessions

**Chat**:
- chat_threads, chat_messages, conversations, conversation_messages

**Notifications**:
- notification_preferences, user_fcm_tokens

**Features**:
- feature_flags, subscriptions

---

## API Routes

### Route Organization (70+ endpoints across 15+ files)

```
/v1/
├── /health                          # Health checks (4 endpoints)
├── /meals                           # Meal management (6 endpoints)
├── /meal-suggestions                # Meal suggestions (7 endpoints - Phase 06 NEW)
├── /meal-plans                      # Meal planning (3 endpoints)
├── /ingredients                     # Ingredient recognition (2 endpoints - NEW v0.3)
├── /foods                           # Food database (2 endpoints)
├── /chat                            # Chat endpoints (3+ endpoints)
│   ├── /threads
│   ├── /threads/{id}/messages
│   └── /ws/{thread_id}              # WebSocket
├── /users                           # User management (5 endpoints)
├── /user-profiles                   # Profile management (3 endpoints)
├── /notifications                   # Push notifications (3 endpoints)
├── /feature-flags                   # Feature management (3 endpoints)
├── /activities                      # Activity tracking (1 endpoint)
├── /daily-meals                     # Daily suggestions (1 endpoint)
├── /webhooks                        # External webhooks (1 endpoint)
└── /monitoring                      # Monitoring/metrics (1 endpoint)
```

---

## Core Services

### Domain Services (Business Logic)

```
src/domain/services/
├── meal_service.py                  # Meal creation, editing, analysis
├── meal_plan_service.py             # Plan generation
├── suggestion_orchestration_service.py  # NEW Phase 06: Session tracking
├── user_service.py                  # User management
├── nutrition_service.py             # Nutrition calculations
├── prompt_generation_service.py     # LLM prompt generation
├── tdee_service.py                  # TDEE calculation
├── portion_calculation_service.py   # Portion sizing
├── meal_plan/                       # 4 refactored components
├── meal_suggestion/                 # 3 refactored components
├── conversation/                    # 3 refactored components
└── (7+ other services)
```

### Infrastructure Services (External Integration)

```
src/infra/services/
├── ai/
│   ├── gemini_service.py           # Google Gemini 2.5 Flash vision
│   └── openai_chat_service.py      # OpenAI GPT-4 chat
├── firebase_service.py              # Firebase auth & messaging
├── firebase_auth_service.py         # Auth helpers
├── pinecone_service.py              # Vector DB
├── scheduled_notification_service.py # Background notifications
└── usda_service.py                  # USDA food database
```

---

## Testing Organization

### Test Structure

```
tests/
├── conftest.py                      # Shared fixtures
├── factories/                       # Test data generators
├── unit/                            # Unit tests (681 tests)
│   ├── domain/
│   │   ├── services/
│   │   ├── test_meal_edit_strategies.py
│   │   └── (others)
│   ├── test_chat_repository.py
│   └── (others)
├── integration/                     # Integration tests
│   ├── test_meal_api.py
│   ├── test_timezone_aware_notifications.py
│   └── (others)
└── fixtures/                        # Test data and mocks
```

### Test Coverage

| Component | Coverage | Status |
|-----------|----------|--------|
| Domain Services | 95%+ | Excellent |
| Repositories | 90%+ | Excellent |
| API Routes | 80%+ | Good |
| Infrastructure | 70%+ | Satisfactory |
| **Overall** | **70%+** | Meets minimum |

### Test Statistics

- **Total Tests**: 681 (all passing)
- **Test Files**: 57
- **Coverage Target**: 70%+ (currently maintained)
- **Test Markers**: unit, integration, slow, asyncio, skip, xfail

---

## Summary

The MealTrack Backend implements a robust 4-layer clean architecture with 145+ source files organized by concern, totaling 474,298 tokens. Completion of all 3 unified phases (Phase 01: Backend 29 files, Phase 02: Mobile 21 files, Phase 03: Legacy cleanup 6 files) resulted in a cohesive, production-ready system.

**Phase Completion Status**:
- ✅ **Phase 01**: Backend unified - 29 files refactored, enum consolidation complete
- ✅ **Phase 02**: Mobile unified - 21 files aligned with backend patterns
- ✅ **Phase 03**: Legacy cleanup - 6 files cleaned, 13 legacy aliases removed

**Architecture Highlights**:
- 4-Layer Clean Architecture with clear separation of concerns
- CQRS pattern with 34+ commands and 30+ queries
- Event-driven architecture with 18+ domain events
- 70+ REST endpoints across 15+ route files
- 27 database tables with 11 migrations
- Comprehensive test suite (681 tests, 70%+ coverage)
- Production-ready with Firebase, Google Gemini, OpenAI, Pinecone integrations
- Greenfield deployment model: No backward compatibility aliases

**Recent Additions (v0.3.0 → v0.4.4)**:
- Phase 06 Session-Based Meal Suggestions (Jan 2026): SuggestionOrchestrationService, session tracking (4h TTL), 7 new endpoints, fallback mechanism
- Phase 03 Legacy Cleanup (Jan 4, 2026): Removed 13 ActivityGoalMapper aliases, simplified fitness goal enum to 3 canonical values
- Phase 03 Large File Refactoring (Dec 31, 2024): 72% LOC reduction (1,963 → 551), 13 new specialized components
- Ingredient recognition API
- User pain points tracking
- Timezone-aware notifications
- RevenueCat webhook integration
