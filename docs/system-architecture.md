# MealTrack Backend - System Architecture

**Version:** 0.4.0
**Last Updated:** December 30, 2024
**Architecture Pattern:** 4-Layer Clean Architecture with CQRS and Event-Driven Design

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Component Interactions](#component-interactions)
4. [Data Flow](#data-flow)
5. [External Integrations](#external-integrations)
6. [Database Design](#database-design)
7. [Query Optimization & N+1 Prevention](#query-optimization--n1-prevention)
8. [Caching Strategy](#caching-strategy)
9. [Event-Driven Architecture](#event-driven-architecture)
10. [Security Architecture](#security-architecture)
11. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### High-Level Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                     Client Applications                         │
│          (Mobile Apps, Web Apps, Third-party clients)           │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTPS/REST/WebSocket
                         ▼
        ┌────────────────────────────────────────┐
        │   FastAPI Application (src/api)        │
        │  - HTTP Routing, Request Handling      │
        │  - Response Serialization              │
        │  - CORS & Middleware                   │
        └────────┬─────────────────────────────┘
                 │ Commands/Queries
                 ▼
    ┌────────────────────────────────────────────────┐
    │  Application Layer (src/app) - CQRS            │
    │  - CommandBus/QueryBus Dispatch                │
    │  - Event Publishing                            │
    │  - Orchestration of Use Cases                  │
    └────────┬──────────────────────────────────────┘
             │ Domain Services & Ports
             ▼
  ┌──────────────────────────────────────────────────┐
  │   Domain Layer (src/domain) - Business Logic     │
  │  - Entities & Value Objects                      │
  │  - Domain Services                               │
  │  - Port Interfaces                               │
  │  - Business Rules & Validation                   │
  └────────┬───────────────────────────────────────┘
           │ Repositories & Adapters
           ▼
      ┌────────────────────────────────────────┐
      │   Infrastructure Layer (src/infra)    │
      │  - Repositories                        │
      │  - Database (MySQL)                    │
      │  - External Services                   │
      │  - Cache Layer (Redis)                 │
      │  - Event Bus                           │
      └────────────────────────────────────────┘
             │               │
             ▼               ▼
       ┌──────────┐    ┌──────────────┐
       │  MySQL   │    │  Redis Cache │
       │  Database│    │              │
       └──────────┘    └──────────────┘
             │
             ▼
    ┌─────────────────────────────────┐
    │   External Services             │
    │  - Google Gemini (Vision AI)    │
    │  - OpenAI (Chat/GPT)            │
    │  - Firebase (Auth, Messaging)   │
    │  - Pinecone (Vector DB)         │
    │  - USDA (Food Database)         │
    │  - Cloudinary (Image Storage)   │
    └─────────────────────────────────┘
```

### Key Characteristics

- **Layered Architecture**: Clear separation of concerns
- **CQRS Pattern**: Separate command (write) and query (read) paths
- **Event-Driven**: Domain events publish to subscribers
- **Dependency Injection**: Loosely coupled components
- **Async-First**: All I/O operations are asynchronous
- **API-First**: RESTful APIs as primary interface

---

## Architecture Layers

### Layer 1: API Layer (Presentation)

**Location**: `src/api/`

**Responsibility**: Handle HTTP requests, validate inputs, serialize responses

**Components**:
```
src/api/
├── main.py                  # FastAPI app initialization
├── base_dependencies.py     # Shared dependency providers
├── routes/v1/               # Route handlers (13 files)
│   ├── meals.py            # Meal endpoints
│   ├── chat.py             # Chat endpoints
│   ├── chat_ws.py          # WebSocket endpoints
│   ├── meal_plans.py       # Meal planning endpoints
│   ├── user_profiles.py    # User profile endpoints
│   ├── users.py            # User management endpoints
│   ├── foods.py            # Food search endpoints
│   ├── notifications.py    # Notification endpoints
│   ├── feature_flags.py    # Feature flag endpoints
│   └── ...
├── schemas/                 # Pydantic models (28+ files)
│   ├── request/            # Request DTOs
│   ├── response/           # Response DTOs
│   └── common/             # Shared schemas
├── mappers/                 # Response mappers
├── dependencies/            # Dependency injection
├── middleware/              # HTTP middleware
│   ├── cors.py
│   ├── auth.py
│   └── error_handler.py
└── utils/                   # Utility functions
```

**Key Patterns**:
- Request validation via Pydantic
- Dependency injection via `FastAPI.Depends()`
- Response mapping (Domain → Schema)
- HTTP status code selection
- Error handling & serialization

**Example Route**:
```python
@router.post("/meals/image/analyze")
async def analyze_meal_image(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    event_bus: EventBus = Depends(get_event_bus),
) -> MealAnalysisResponse:
    """Analyze meal image and extract nutrition."""
    command = AnalyzeMealImageCommand(
        file_contents=await file.read(),
        content_type=file.content_type,
        user_id=current_user.id,
    )
    result = await event_bus.send(command)
    return MealAnalysisResponse.from_result(result)
```

### Layer 2: Application Layer

**Location**: `src/app/`

**Responsibility**: Orchestrate commands/queries, coordinate domain services, manage events

**Components**:
```
src/app/
├── commands/               # Command definitions (19+ files)
│   ├── meal/
│   ├── meal_plan/
│   ├── chat/
│   ├── user/
│   ├── notification/
│   └── ...
├── queries/                # Query definitions (15+ files)
│   ├── meal/
│   ├── meal_plan/
│   ├── chat/
│   ├── food/
│   └── ...
├── events/                 # Domain event definitions
│   ├── meal/
│   ├── meal_plan/
│   ├── user/
│   └── ...
└── handlers/               # Handler implementations
    ├── command_handlers/   # 22+ implementations
    ├── query_handlers/     # 18+ implementations
    └── event_handlers/     # Subscribers
```

**CQRS Pattern**:

```python
# Commands (State Changes)
@dataclass
class CreateMealCommand(Command):
    user_id: str
    foods: List[FoodItem]
    consumed_at: datetime

# Queries (Reads)
@dataclass
class GetMealByIdQuery(Query):
    meal_id: str
    user_id: str

# Command Handler
class CreateMealCommandHandler:
    async def handle(self, command: CreateMealCommand) -> MealResult:
        # Create meal, validate, publish events
        meal = await self._meal_service.create(command)
        await self._event_bus.publish(MealCreatedEvent(...))
        return meal

# Query Handler
class GetMealByIdQueryHandler:
    async def handle(self, query: GetMealByIdQuery) -> Meal:
        # Read from cache/database
        return await self._meal_repository.get_by_id(query.meal_id)
```

**Event Handling**:
```python
# Domain events
@dataclass
class MealAnalyzedEvent(DomainEvent):
    meal_id: str
    user_id: str
    nutrition: NutritionData
    timestamp: datetime

# Event handlers (subscribers)
class OnMealAnalyzed:
    async def handle(self, event: MealAnalyzedEvent) -> None:
        # Send notification, update cache, trigger workflows
        await self._notification_service.notify_user(event.user_id)
        await self._cache_service.invalidate(f"meal:{event.meal_id}")
```

**Key Benefits**:
- API routes don't know about specific handlers
- Easy to test command/query handlers in isolation
- Event-driven side effects (notifications, cache invalidation)
- Clear separation between reads and writes

### Layer 3: Domain Layer

**Location**: `src/domain/`

**Responsibility**: Encapsulate core business logic, independent of frameworks

**Components**:
```
src/domain/
├── model/                  # Domain entities (25+)
│   ├── meal/
│   │   ├── meal.py         # Meal entity
│   │   ├── food_item.py    # FoodItem value object
│   │   └── nutrition.py    # Nutrition data
│   ├── meal_planning/
│   │   ├── meal_plan.py
│   │   └── meal_plan_day.py
│   ├── user/
│   ├── nutrition/
│   ├── chat/
│   ├── notification/
│   └── ...
├── services/               # Domain services (15+)
│   ├── meal_service.py
│   ├── meal_plan_service.py
│   ├── user_service.py
│   ├── nutrition_service.py
│   ├── prompt_generation_service.py
│   └── ...
├── strategies/            # Strategy implementations
│   ├── meal_edit_strategies.py
│   └── meal_analysis_strategies.py
├── ports/                 # Port interfaces
│   ├── repositories/
│   └── services/
├── parsers/               # Response parsing
├── mappers/               # Domain model mappings
├── prompts/               # AI prompt templates
└── constants/             # Enums & constants
```

**Domain Models**:
```python
# Example: Meal entity
@dataclass
class Meal:
    """Core meal entity."""

    meal_id: str
    user_id: str
    meal_items: List[MealItem]
    nutrition: Nutrition
    consumed_at: datetime
    status: MealStatus

    def edit_meal(self, strategy: MealEditStrategy) -> "Meal":
        """Apply edit strategy to meal."""
        return strategy.execute(self)

    def get_daily_summary(self) -> Dict[str, float]:
        """Get nutrition summary for display."""
        return {
            "calories": self.nutrition.calories,
            "protein": self.nutrition.protein,
            "carbs": self.nutrition.carbs,
            "fat": self.nutrition.fat,
        }

# Value object
@dataclass(frozen=True)
class Nutrition:
    """Immutable nutrition data."""
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None

    def meets_target(self, target: "Nutrition") -> bool:
        """Check if nutrition meets target."""
        tolerance = 0.15  # ±15%
        return abs(self.calories - target.calories) / target.calories < tolerance
```

**Domain Services**:
```python
class MealService:
    """Orchestrates meal operations."""

    def __init__(
        self,
        meal_repo: MealRepository,
        nutrition_service: NutritionService,
        ai_service: AIService,
    ):
        self._meal_repo = meal_repo
        self._nutrition_service = nutrition_service
        self._ai_service = ai_service

    async def analyze_and_create_meal(
        self,
        image_path: str,
        user_id: str,
    ) -> Meal:
        """Analyze image and create meal."""
        # AI analysis
        analysis = await self._ai_service.analyze(image_path)

        # Create meal with nutrition
        nutrition = await self._nutrition_service.calculate(analysis)

        meal = Meal(
            meal_id=generate_id(),
            user_id=user_id,
            meal_items=analysis.items,
            nutrition=nutrition,
            consumed_at=datetime.utcnow(),
            status=MealStatus.READY,
        )

        # Persist
        return await self._meal_repo.save(meal)
```

**Ports (Interfaces)**:
```python
# Abstract repository interface
class MealRepository(Protocol):
    async def get_by_id(self, meal_id: str) -> Optional[Meal]:
        ...

    async def save(self, meal: Meal) -> Meal:
        ...

# Abstract service interface
class AIService(Protocol):
    async def analyze(self, image_path: str) -> AnalysisResult:
        ...
```

**Key Characteristics**:
- No framework dependencies
- Pure business logic
- High testability
- Reusable across layers
- Clear domain language

### Layer 4: Infrastructure Layer

**Location**: `src/infra/`

**Responsibility**: Implement technical details, external integrations, data persistence

**Components**:
```
src/infra/
├── database/              # Database access
│   ├── config.py          # Connection setup
│   ├── models/            # SQLAlchemy ORM (16+ models)
│   └── migration_manager.py
├── repositories/          # Data access layer (7+ repos)
│   ├── meal_repository.py
│   ├── user_repository.py
│   ├── chat_repository.py
│   └── ...
├── services/              # External service adapters
│   ├── ai/
│   │   ├── gemini_service.py        # Google Gemini API
│   │   └── openai_chat_service.py   # OpenAI GPT-4
│   ├── firebase_service.py          # Firebase SDK
│   ├── firebase_auth_service.py     # Auth helpers
│   ├── pinecone_service.py          # Vector embeddings
│   ├── scheduled_notification_service.py
│   └── usda_service.py              # Food database
├── adapters/              # Third-party adapters
│   ├── cloudinary_adapter.py        # Image storage
│   └── storage_factory.py
├── cache/                 # Caching layer
│   ├── redis_client.py
│   ├── cache_service.py
│   ├── cache_keys.py
│   ├── decorators.py
│   └── metrics.py
├── event_bus/             # Event dispatcher
│   └── event_bus.py
├── websocket/             # WebSocket management
│   └── connection_manager.py
└── config/                # Configuration
    └── settings.py
```

**Repository Implementation**:
```python
class MealRepository:
    """Implements meal data access."""

    def __init__(self, session: AsyncSession, mapper: MealMapper):
        self._session = session
        self._mapper = mapper

    async def get_by_id(self, meal_id: str) -> Optional[Meal]:
        """Get meal from database."""
        orm_model = await self._session.get(MealORM, meal_id)
        if not orm_model:
            return None
        return self._mapper.to_domain(orm_model)

    async def save(self, meal: Meal) -> Meal:
        """Save meal to database."""
        orm_model = self._mapper.to_orm(meal)
        self._session.add(orm_model)
        await self._session.flush()
        return meal
```

**External Service Adapter**:
```python
class GeminiService:
    """Integrates with Google Gemini API."""

    def __init__(self, api_key: str):
        self._client = genai.Client(api_key=api_key)

    async def analyze_meal_image(
        self,
        image_path: str,
    ) -> MealAnalysisResult:
        """Call Gemini API for image analysis."""
        with open(image_path, "rb") as f:
            image_data = f.read()

        response = await self._client.vision.analyze(
            image=image_data,
            prompt=MEAL_ANALYSIS_PROMPT,
        )

        # Parse response and return domain model
        return self._parse_response(response)
```

---

## Component Interactions

### Request-Response Flow

```
1. HTTP Request
   ↓
2. FastAPI Route Handler
   ├─ Validate input (Pydantic)
   ├─ Get current user
   └─ Create command/query
   ↓
3. Event Bus Dispatcher
   ├─ Route to handler
   └─ Execute handler
   ↓
4. Command/Query Handler
   ├─ Call domain services
   ├─ Coordinate repositories
   └─ Publish events
   ↓
5. Domain Services
   ├─ Implement business logic
   ├─ Validate rules
   └─ Call repositories
   ↓
6. Repositories
   ├─ Map domain → ORM
   ├─ Execute database query
   └─ Return results
   ↓
7. Response Mapping
   ├─ Map domain → schema
   └─ Serialize to JSON
   ↓
8. HTTP Response
```

### Example: Analyze Meal Image

```
POST /v1/meals/image/analyze
{
  "file": <image_file>
}

1. api/routes/v1/meals.py::analyze_meal_image()
   ↓
   request_file = UploadFile(file)
   command = AnalyzeMealImageCommand(...)

2. event_bus.send(command)
   ↓
   CommandHandler::handle(AnalyzeMealImageCommand)

3. meal_service.analyze_and_create_meal()
   ├─ gemini_service.analyze_image()  # Google Gemini API
   ├─ nutrition_service.calculate()
   └─ meal_repository.save()

4. Events published
   ├─ MealAnalyzedEvent
   └─ Subscribers receive:
      ├─ notification_service.notify_user()
      └─ cache_service.invalidate()

5. Response mapped
   └─ MealAnalysisResponse

6. Return 200 OK with meal_id
```

---

## Data Flow

### Meal Image Upload Flow

```
┌─────────────────────────────────────────────────┐
│ 1. User uploads meal image                       │
│    POST /v1/meals/image/analyze                  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
        ┌─────────────────────────────┐
        │ 2. API Route Handler         │
        │   - Parse file upload       │
        │   - Create command          │
        └─────────────┬───────────────┘
                      │
                      ▼
              ┌───────────────────────┐
              │ 3. Event Bus Dispatch │
              │   - Route to handler  │
              └─────────┬─────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │ 4. Command Handler                 │
        │   - Call meal_service             │
        │   - Coordinate operations         │
        └─────────────┬─────────────────────┘
                      │
        ┌─────────────┴──────────┬─────────────┐
        │                        │             │
        ▼                        ▼             ▼
   ┌──────────────┐    ┌─────────────────┐  ┌──────────────┐
   │ Gemini API   │    │ Nutrition Svc   │  │ Meal Repo    │
   │ - Analyze    │    │ - Calculate     │  │ - Save to DB │
   │ - Extract    │    │   macros        │  │              │
   │   foods      │    │                 │  │              │
   └──────────────┘    └─────────────────┘  └──────────────┘
        │                      │                    │
        └──────────────┬───────┴────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │ 5. Events Published              │
        │   - MealAnalyzedEvent            │
        └──────────┬───────────────────────┘
                   │
        ┌──────────┴──────────┬─────────────────┐
        │                     │                 │
        ▼                     ▼                 ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │ Notification │   │ Cache Svc    │   │ Analytics    │
   │ Service      │   │ - Invalidate │   │ Service      │
   │ - Send push  │   │   user data  │   │              │
   │   to device  │   │              │   │              │
   └──────────────┘   └──────────────┘   └──────────────┘
        │                     │                    │
        └─────────────────────┴────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ 6. Response to Client │
                    │ {                    │
                    │   "meal_id": "123",  │
                    │   "status": "READY"  │
                    │ }                    │
                    └──────────────────────┘
```

### Meal Query Flow

```
GET /v1/meals/{meal_id}

1. API Route
   └─ GetMealByIdQuery(meal_id)

2. Query Bus
   └─ GetMealByIdQueryHandler

3. Check Cache
   ├─ Cache HIT: Return cached meal
   └─ Cache MISS: Continue

4. Load from Database
   ├─ MealRepository.get_by_id()
   ├─ Query: SELECT * FROM meals WHERE id = ?
   └─ Map ORM → Domain Model

5. Update Cache
   └─ cache.set(key, meal, ttl=300s)

6. Return Response
   └─ MealResponse(meal)
```

---

## External Integrations

### Integration Points

```
┌──────────────────────┐
│   MealTrack Backend  │
│   (v0.3.0)           │
└──────┬───────────────┘
       │
       ├─► Google Gemini 2.0 API
       │   - Meal image analysis
       │   - Vision AI processing
       │   - Food recognition
       │   - Ingredient identification (NEW)
       │
       ├─► OpenAI GPT-4 API
       │   - Chat responses
       │   - Meal planning
       │   - Nutrition advice
       │   - Meal suggestions (NEW)
       │
       ├─► Firebase
       │   - User authentication
       │   - Push notifications (FCM)
       │   - Timezone-aware scheduling (NEW)
       │   - User ID management
       │
       ├─► Pinecone
       │   - Vector embeddings
       │   - Semantic search
       │   - Food similarity queries
       │
       ├─► USDA FoodData Central
       │   - Nutrition database
       │   - Food item lookup
       │   - Macro/micro nutrients
       │
       ├─► Cloudinary
       │   - Image storage & CDN
       │   - Image optimization
       │   - URL generation
       │
       ├─► RevenueCat (NEW)
       │   - Subscription management
       │   - Webhook events
       │   - User entitlements
       │
       └─► MySQL Database
           - Persistent storage
           - Transaction management
           - Data integrity
           - 11 migrations (up-to-date)
```

### Service Integration Pattern

```python
# Adapter pattern for external services
class GeminiService:
    """Adapter for Google Gemini API."""

    async def analyze_meal_image(
        self,
        image_path: str,
    ) -> MealAnalysisResult:
        """Call Gemini API and return domain model."""
        try:
            response = await self._client.analyze_image(image_path)
            return self._parse_response(response)
        except GeminiAPIError as e:
            logger.error(f"Gemini analysis failed: {e}")
            raise MealAnalysisError(str(e)) from e

# Error handling for external services
try:
    result = await gemini_service.analyze(image_path)
except MealAnalysisError:
    # Retry logic
    for attempt in range(3):
        try:
            result = await gemini_service.analyze(image_path)
            break
        except MealAnalysisError:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            if attempt == 2:
                raise
```

---

## Database Design

### Entity-Relationship Diagram (Simplified)

```sql
users
├─ id (PK)
├─ firebase_uid (UNIQUE)
├─ email
├─ created_at
└─ updated_at

user_profiles (1:1 with users)
├─ id (PK)
├─ user_id (FK)
├─ age
├─ weight
├─ height
└─ activity_level

meals (N:1 with users)
├─ id (PK)
├─ user_id (FK)
├─ consumed_at
├─ status (ENUM)
└─ created_at

meal_images (N:1 with meals)
├─ id (PK)
├─ meal_id (FK)
├─ image_url
└─ uploaded_at

food_items (N:1 with meals)
├─ id (PK)
├─ meal_id (FK)
├─ food_id (USDA FDC ID)
├─ quantity
├─ unit
└─ portion_description

nutrition (1:1 with meals)
├─ id (PK)
├─ meal_id (FK)
├─ calories
├─ protein
├─ carbs
├─ fat
└─ fiber

meal_plans (N:1 with users)
├─ id (PK)
├─ user_id (FK)
├─ start_date
├─ end_date
└─ preferences (JSON)

meal_plan_days (N:1 with meal_plans)
├─ id (PK)
├─ plan_id (FK)
├─ day_number
└─ target_calories

planned_meals (N:1 with meal_plan_days)
├─ id (PK)
├─ day_id (FK)
├─ meal_id (FK)
└─ meal_type (ENUM: breakfast, lunch, dinner, snack)

chat_threads (N:1 with users)
├─ id (PK)
├─ user_id (FK)
├─ created_at
└─ updated_at

chat_messages (N:1 with chat_threads)
├─ id (PK)
├─ thread_id (FK)
├─ role (ENUM: user, assistant)
├─ content (TEXT)
└─ created_at

feature_flags
├─ id (PK)
├─ flag_name (UNIQUE)
├─ enabled (BOOLEAN)
├─ rollout_percentage (INT 0-100)
└─ updated_at
```

### Key Design Decisions

1. **No Direct Foreign Keys to USDA Foods**: Food items reference USDA FDC ID as string (external system)
2. **Nutrition Denormalized**: Stored with meal for historical accuracy (not recalculated)
3. **Timestamps on Everything**: Created_at and updated_at for auditing
4. **Status Enums**: Meal status, message role stored as ENUM for type safety
5. **JSON Columns**: Preferences stored as JSON for flexibility
6. **Indexes on Foreign Keys**: All FK columns indexed for query performance

---

## Query Optimization & N+1 Prevention

### Problem: N+1 Query Pattern

Without eager loading, each relationship access triggers additional queries:

```python
# This causes N+1 queries
meals = get_meals(user_id)  # 1 query: SELECT * FROM meals
for meal in meals:          # N queries: SELECT * FROM nutrition WHERE meal_id = ?
    print(meal.nutrition)
```

**Impact**:
- GET /meals endpoint → 1 + N queries (N = number of meals)
- GET /meal-plans/{id} → 1 + days + (days * meals) queries (nested)

### Solution: Eager Loading with SQLAlchemy

Define load strategies at repository module level:

```python
from sqlalchemy.orm import joinedload, selectinload

# Meal Repository
_MEAL_LOAD_OPTIONS = (
    joinedload(DBMeal.user),                    # M2O: LEFT JOIN
    selectinload(DBMeal.nutrition)
    .selectinload(DBNutrition.food_items),      # O2M: SELECT IN (nested)
    selectinload(DBMeal.images),                # O2M: SELECT IN
)

# Apply in queries
async def get_by_id(self, meal_id: str) -> Optional[Meal]:
    result = await self.session.execute(
        select(DBMeal)
        .options(*_MEAL_LOAD_OPTIONS)
        .where(DBMeal.id == meal_id)
    )
    return self._to_domain(result.scalar_one_or_none())
```

### Eager Loading Strategies

| Relationship | Strategy | Use Case | Example |
|--------------|----------|----------|---------|
| Many-to-One | `joinedload()` | Parent objects (single result) | Meal → User |
| One-to-Many | `selectinload()` | Collections (many results) | Meal → FoodItems |
| Nested | Chained `selectinload()` | Deep relationships | MealPlan → Days → Meals |

**Key Metrics (Phase 02 Audit)**:
- Query logging enabled in development (config.py line 102)
- `meal_repository.py`: Proper eager loading implemented (_MEAL_LOAD_OPTIONS)
- `meal_plan_repository.py`: Nested eager loading implemented (_MEAL_PLAN_LOAD_OPTIONS)
- `notification_repository.py`: Minor N+1 in preference loop (lines 303-305) - non-critical, pending optimization

### Development Practices

Enable query logging during development to verify optimization:

```bash
# In .env
ENVIRONMENT=development

# Check logs for query count reduction
# Should see: SELECT, SELECT IN, SELECT IN (not 1 + N queries)
```

### Affected Repositories

- ✅ **meal_repository.py**: Eager loading configured
- ✅ **meal_plan_repository.py**: Nested eager loading configured
- ⚠️ **notification_repository.py**: Preference queries in loop (low priority)
- ✅ **user_repository.py**: Standard eager loading

---

## Caching Strategy

### Cache Layers

```
┌──────────────────────────────────────────┐
│         Application Layer Cache          │
│  (In-memory, Request-scoped)             │
└──────────────────┬───────────────────────┘
                   │
                   ▼
    ┌────────────────────────────────┐
    │      Redis Cache Layer         │
    │  (Distributed, TTL-based)      │
    └────────────┬───────────────────┘
                 │
                 ▼
      ┌───────────────────────┐
      │   Database Layer      │
      │  (Source of truth)    │
      └───────────────────────┘
```

### Cache Key Structure

```python
# User data
user:{user_id}                      # TTL: 3600s (1 hour)
user:{user_id}:profile             # TTL: 1800s (30 min)
user:{user_id}:goals               # TTL: 1800s (30 min)

# Meal data
meal:{meal_id}                      # TTL: 7200s (2 hours)
meal:{user_id}:history             # TTL: 300s (5 min) - pagination cache
meal:{user_id}:daily_summary:{date} # TTL: 3600s (1 hour)

# Food/Nutrition
food:{food_id}                      # TTL: 86400s (24 hours)
food:search:{query_hash}            # TTL: 3600s (1 hour)

# Meal Plan
meal_plan:{plan_id}                 # TTL: 1800s (30 min)
meal_plan:{user_id}:current         # TTL: 900s (15 min)

# Feature Flags
feature_flag:{flag_name}            # TTL: 300s (5 min)
feature_flags:all                   # TTL: 300s (5 min)
```

### Cache Invalidation

```python
# Invalidation triggers
on_meal_created → invalidate(f"user:{user_id}:daily_summary:{date}")
on_meal_edited → invalidate(f"meal:{meal_id}", f"user:{user_id}:daily_summary")
on_meal_deleted → invalidate(f"meal:{meal_id}", f"user:{user_id}:history")
on_goals_updated → invalidate(f"user:{user_id}:goals")

# Cache warming for hot paths
async def warm_cache():
    # Pre-load frequently accessed data
    for user_id in active_users:
        await cache.set(f"user:{user_id}", user_data)
        await cache.set(f"user:{user_id}:today_meals", today_meals)
```

### Caching Patterns

```python
# Decorator pattern for transparent caching
@cache_result(ttl=3600)
async def get_meal_by_id(meal_id: str) -> Meal:
    return await repository.get_by_id(meal_id)

# Manual caching for complex queries
async def get_user_daily_summary(user_id: str, date: str) -> Summary:
    cache_key = f"summary:{user_id}:{date}"

    # Try cache first
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Load from database
    summary = await service.calculate_summary(user_id, date)

    # Store in cache
    await cache.set(cache_key, summary, ttl=3600)

    return summary
```

---

## Event-Driven Architecture

### Event Publishing Flow

```
Command Executed
    ↓
Domain Entity State Changes
    ↓
Domain Events Created
    ↓
Events Added to Event Store (Application Layer)
    ↓
Event Bus Publishes Events
    ├─► Event Handler 1 (Notification Service)
    ├─► Event Handler 2 (Cache Invalidation)
    ├─► Event Handler 3 (Analytics)
    └─► Event Handler N (Custom Logic)
```

### Event Examples

```python
# Meal domain events
@dataclass
class MealCreatedEvent(DomainEvent):
    meal_id: str
    user_id: str
    consumed_at: datetime

@dataclass
class MealAnalyzedEvent(DomainEvent):
    meal_id: str
    nutrition: NutritionData
    timestamp: datetime

@dataclass
class MealDeletedEvent(DomainEvent):
    meal_id: str
    user_id: str

# User domain events
@dataclass
class UserOnboardedEvent(DomainEvent):
    user_id: str
    firebase_uid: str

@dataclass
class UserGoalsUpdatedEvent(DomainEvent):
    user_id: str
    daily_calorie_goal: int
```

### Event Handlers

```python
# Subscribe to events
class OnMealAnalyzed:
    """Handle meal analyzed event."""

    def __init__(
        self,
        notification_service: NotificationService,
        cache_service: CacheService,
    ):
        self._notification = notification_service
        self._cache = cache_service

    async def handle(self, event: MealAnalyzedEvent) -> None:
        # 1. Send notification to user
        await self._notification.send_push(
            user_id=event.meal_id.split(":")[0],
            title="Meal Analysis Complete",
            body=f"Calories: {event.nutrition.calories}",
        )

        # 2. Invalidate cache
        await self._cache.invalidate(f"meal:{event.meal_id}")

        # 3. Update analytics
        await self._analytics.track_meal_analyzed(event)
```

---

## Security Architecture

### Authentication Flow

```
1. User Login
   ├─ Firebase Auth (email/password or OAuth)
   └─ Returns ID token

2. Token Validation
   ├─ Each request includes Authorization: Bearer <token>
   ├─ FastAPI dependency verifies token
   └─ Extract user_id from token

3. User Context
   └─ Pass user to handlers via dependency injection

4. Authorization Check
   ├─ Verify user owns resource
   └─ Enforce role-based access (if applicable)
```

### API Security

```python
# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.mealtrack.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_credentials=True,
)

# Rate limiting
@router.post("/meals")
@rate_limit(requests=100, period=60)  # 100 requests per minute
async def create_meal(request: MealRequest) -> MealResponse:
    pass

# Input validation
class MealRequest(BaseModel):
    foods: List[FoodItemRequest] = Field(
        ...,
        min_items=1,
        max_items=50
    )
    notes: Optional[str] = Field(None, max_length=500)

    @validator("notes")
    def validate_notes(cls, v):
        if v and "<script>" in v.lower():
            raise ValueError("Invalid content")
        return v
```

### Data Protection

```python
# Encrypted sensitive data
class UserProfile(Base):
    __tablename__ = "user_profiles"

    # Sensitive fields encrypted at rest
    health_data = Column(String, nullable=True)  # Encrypted before storage

    def set_health_data(self, data: Dict) -> None:
        """Encrypt and store health data."""
        encrypted = encrypt_sensitive_data(data)
        self.health_data = encrypted

    def get_health_data(self) -> Dict:
        """Decrypt and retrieve health data."""
        return decrypt_sensitive_data(self.health_data)

# Audit logging
async def log_action(user_id: str, action: str, resource_id: str):
    """Log user actions for auditing."""
    await audit_repository.save(AuditLog(
        timestamp=datetime.utcnow(),
        user_id=user_id,
        action=action,
        resource_id=resource_id,
    ))
```

---

## Deployment Architecture

### Container Structure

```
Dockerfile (Multi-stage)

Stage 1: Builder
├─ Python 3.13 base image
├─ Install dependencies
└─ Build wheels

Stage 2: Runtime
├─ Python 3.13 slim
├─ Copy wheels from builder
├─ Copy source code
├─ Expose port 8000
└─ CMD: uvicorn src.api.main:app
```

### Kubernetes Deployment (Future)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mealtrack-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mealtrack-api
  template:
    metadata:
      labels:
        app: mealtrack-api
    spec:
      containers:
      - name: mealtrack-api
        image: ghcr.io/mealtrack/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mealtrack-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Scaling Strategy

```
Horizontal Scaling (Load Distribution)
├─ API instances behind load balancer
├─ Database read replicas
└─ Redis cluster for distributed caching

Vertical Scaling (Instance Power)
├─ Increase CPU for compute-heavy tasks
└─ Increase memory for caching layer

Caching Strategy
├─ Redis for hot data
├─ Query result caching
└─ Page caching for static content

Database Optimization
├─ Index frequently queried columns
├─ Partition large tables by user_id
└─ Archive historical data
```

---

## Summary

The MealTrack Backend employs a sophisticated 4-layer clean architecture with CQRS pattern for scalability. External integrations with Google Gemini, OpenAI, Firebase, and other services are abstracted through adapters, maintaining loose coupling. The event-driven architecture enables reactive features like real-time notifications and cache invalidation. Redis caching improves performance, while MySQL provides durable storage with comprehensive transaction support.

Key architectural strengths:
- Clear separation of concerns across layers
- CQRS for independent scaling of read/write paths
- Event-driven for loose coupling between components
- Extensive caching for high-performance queries
- Comprehensive security with authentication and authorization
- Observable through structured logging and monitoring
