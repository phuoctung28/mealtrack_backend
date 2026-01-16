# MealTrack Backend - System Architecture

**Last Updated:** January 16, 2026
**Version:** 0.4.7
**Architecture**: 4-Layer Clean Architecture + CQRS + Event-Driven
**Source**: Scout-verified analysis of 408 files (~37K LOC)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Layer Details](#layer-details)
3. [CQRS & Event Bus](#cqrs--event-bus)
4. [Database Architecture](#database-architecture)
5. [External Integrations](#external-integrations)
6. [Security Architecture](#security-architecture)
7. [Performance & Scalability](#performance--scalability)
8. [Deployment Architecture](#deployment-architecture)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (74 files)                    │
│  HTTP Routing │ Pydantic Validation │ Auth │ Middleware      │
└────────────────────────┬────────────────────────────────────┘
                         │ Commands/Queries
┌────────────────────────▼────────────────────────────────────┐
│              Application Layer (136 files)                   │
│  CQRS Handlers │ Event Publishing │ App Services             │
└────────────────────────┬────────────────────────────────────┘
                         │ Domain Services
┌────────────────────────▼────────────────────────────────────┐
│                Domain Layer (124 files)                      │
│  Business Logic │ Domain Models │ Port Interfaces            │
└────────────────────────┬────────────────────────────────────┘
                         │ Port Implementations
┌────────────────────────▼────────────────────────────────────┐
│            Infrastructure Layer (74 files)                   │
│  DB │ Cache │ External APIs │ Event Bus │ Config             │
└─────────────────────────────────────────────────────────────┘
```

### Layer Statistics

| Layer | Files | LOC | Purpose |
|-------|-------|-----|---------|
| API | 74 | ~8,244 | HTTP presentation |
| Application | 136 | ~5,967 | CQRS orchestration |
| Domain | 124 | ~14,236 | Business logic |
| Infrastructure | 74 | ~8,505 | Technical implementation |
| **Total** | **408** | **~37,000** | |

---

## Layer Details

### API Layer (`src/api/`)

**Components**:
- **14 Route Modules** (2,388 LOC): Health, Meals, Users, Profiles, Chat, Notifications, Meal Plans, Suggestions, Activities, Ingredients, Webhooks, Monitoring, Feature Flags, Foods
- **34 Pydantic Schemas** (2,530 LOC): Request/response DTOs with validation
- **8 Mappers** (1,026 LOC): API ↔ Domain transformations
- **3 Middleware Layers** (530 LOC): CORS, Request Logging, Dev Auth Bypass
- **2 DI Providers** (706 LOC): Auth (Firebase JWT), Event Bus (PyMediator)

**Responsibilities**:
1. Receive HTTP requests
2. Validate via Pydantic schemas
3. Dispatch commands/queries to event bus
4. Map domain models to response DTOs
5. Handle authentication/authorization

**Key Endpoints** (80+ total):
- `POST /v1/meals/image/analyze` - Immediate meal analysis
- `POST /v1/meals/manual` - Create meal from USDA foods
- `GET /v1/meals/{id}` - Fetch meal details
- `GET /v1/user-profiles/tdee` - TDEE calculation
- `POST /v1/meal-plans/weekly/ingredient-based` - Generate weekly plan
- `GET /v1/meal-suggestions` - Get personalized suggestions
- `POST /v1/chat/threads/{id}/messages` - Send chat message
- `WS /v1/chat/ws` - Real-time chat

**Middleware Chain**:
1. **CORSMiddleware** - Allow all origins (TODO: restrict in prod)
2. **RequestLoggerMiddleware** - Request ID, timing, slow request detection (>1s)
3. **DevAuthBypassMiddleware** - Inject dev user in development mode

**Authentication Flow**:
```
Client → Authorization: Bearer <token>
       → verify_firebase_token()
       → Firebase Admin SDK
       → get_current_user_id()
       → Database user lookup
       → UUID user_id
```

### Application Layer (`src/app/`)

**Components**:
- **21 Commands** (596 LOC): Write operations
- **20 Queries** (359 LOC): Read operations
- **11+ Domain Events** (448 LOC): Historical facts
- **49 Handlers** (4,008 LOC): 31 command, 18 query, 1 event
- **3 Application Services** (556 LOC): Chat orchestration, AI response coordination, notification broadcasting

**CQRS Breakdown**:

**Commands** (user intent to change state):
- User: SyncUser, UpdateUserMetrics, SaveUserOnboarding, DeleteUser
- Meal: CreateManualMeal, EditMeal, DeleteMeal, UploadMealImageImmediately
- Planning: GenerateWeeklyIngredientBasedMealPlan, GenerateDailyMealSuggestions, GenerateSingleMeal
- Chat: CreateThread, SendMessage, DeleteThread
- Notifications: RegisterFcmToken, DeleteFcmToken, UpdateNotificationPreferences

**Queries** (read-only data retrieval):
- User: GetUserByFirebaseUid, GetUserProfile, GetUserMetrics, GetUserTdee
- Meal: GetMealById, GetDailyMacros
- Planning: GetMealPlan, GetMealsByDate, GetMealsFromPlanByDate
- Food: SearchFoods, GetFoodDetails
- Chat: GetThread, GetThreads, GetMessages

**Domain Events** (things that happened):
- Meal: MealImageUploadedEvent, MealAnalysisStartedEvent, MealNutritionUpdatedEvent, MealEditedEvent
- Planning: MealPlanGeneratedEvent, MealReplacedEvent
- User: UserOnboardedEvent, UserProfileUpdatedEvent
- Chat: MessageSentEvent, ThreadCreatedEvent, ThreadDeletedEvent

**Event Flow Example**:
```
1. API receives POST /v1/meals/image/analyze
2. Route creates UploadMealImageImmediatelyCommand
3. EventBus.send() → UploadMealImageImmediatelyCommandHandler
4. Handler:
   - Uploads image to Cloudinary
   - Creates Meal with PROCESSING status
   - Publishes MealImageUploadedEvent
5. EventBus.publish() → MealAnalysisEventHandler (background)
6. Background handler:
   - Updates status to ANALYZING
   - Calls VisionAIService (Gemini)
   - Parses nutrition with GPTResponseParser
   - Updates meal to READY
7. Returns Meal to API layer immediately (step 4)
```

### Domain Layer (`src/domain/`)

**8 Bounded Contexts**:
1. **Meal**: Meal, MealImage, Ingredient, MealStatus
2. **Nutrition**: Nutrition, FoodItem, Macros, Micros, Food
3. **User**: Activity, TdeeRequest, TdeeResponse, MacroTargets, Sex, ActivityLevel, Goal
4. **Meal Planning**: MealPlan, PlannedMeal, DayPlan, UserPreferences, DietaryPreference
5. **Conversation**: Conversation, Message, ConversationState, PromptContext
6. **Notification**: UserFcmToken, NotificationPreferences, PushNotification, DeviceType
7. **AI**: GPTAnalysisResponse, GPTFoodItem, GPTResponseError hierarchy
8. **Chat**: Thread, Message, ThreadStatus, MessageRole

**50 Domain Services**:
- **MealCoreService**: Meal operations, nutrition calculation, meal type determination (time-based)
- **TdeeCalculationService**: BMR + TDEE + macro calculations with auto-formula selection
- **NutritionCalculationService**: Nutrition from USDA FDC, Pinecone, or None (priority-based)
- **PlanOrchestrator**: Generate, save, update, delete meal plans
- **SuggestionOrchestrationService**: Session-based suggestions with 4h TTL
- **TranslationService**: Multi-language support (7 languages)
- **NotificationService**: FCM push notifications

**6 Analysis Strategies** (Strategy Pattern):
1. **BasicAnalysisStrategy**: No context
2. **PortionAwareAnalysisStrategy**: Adjusts for portion size (e.g., 200g, 1 cup)
3. **IngredientAwareAnalysisStrategy**: Uses known ingredient list
4. **WeightAwareAnalysisStrategy**: Adjusts for total weight in grams
5. **IngredientIdentificationStrategy**: Identifies single ingredient from photo
6. **UserContextAwareAnalysisStrategy**: Incorporates user description

**15 Port Interfaces** (Dependency Inversion):
- **Repository Ports** (7): MealRepositoryPort, UserRepositoryPort, MealPlanRepositoryPort, etc.
- **Service Ports** (8): VisionAIServicePort, MealGenerationServicePort, FoodDataServicePort, ImageStorePort, etc.

**Business Rules**:
- **TDEE Calculation**: Auto-select Katch-McArdle (if body_fat%) else Mifflin-St Jeor
- **Meal Type Determination**: Time-based (5-10:30 breakfast, 11-14:30 lunch, 17-21 dinner, else snack)
- **Calorie Distribution**: Breakfast 25%, Lunch 35%, Dinner 30%, Snack 10%
- **Meal Planning**: Use ONLY available ingredients, min 3 days before repeat, max 2 same-cuisine per week

### Infrastructure Layer (`src/infra/`)

**Components**:
- **11 Database Tables**: User, UserProfile, Subscription, Meal, MealImage, Nutrition, FoodItem, MealPlan, NotificationPreferences, UserFcmToken, Thread, Message
- **10+ Repositories**: Smart sync with diff-based updates, eager loading
- **External Services**: Firebase (FCM), Cloudinary (images), Gemini (AI), Pinecone (vector search), RevenueCat (subscriptions)
- **Redis Cache**: Graceful degradation, JSON serialization, cache-aside pattern
- **PyMediator Event Bus**: Singleton registry, async event handling

**Database Architecture**:
- **Engine**: MySQL 8.0 + SQLAlchemy 2.0
- **Session Management**: Request-scoped sessions via ContextVar (singleton-safe)
- **Connection Pool**: Dynamic sizing (POOL_SIZE=20, MAX_OVERFLOW=30)
- **Migrations**: Alembic with auto-migration on startup

**Repository Pattern**:
```python
class MealRepository(MealRepositoryPort):
    def save(self, meal: Meal) -> Meal:
        # Smart sync: update existing or create new
        # Diff-based updates for nested entities (food items)
        # Preserve IDs, update/add/remove as needed
        pass

    def find_by_id(self, meal_id: str) -> Optional[Meal]:
        # Eager loading with joinedload
        # Convert DB model to domain entity
        pass
```

**Cache Strategy**:
- **Pattern**: Cache-aside
- **Serialization**: JSON with Pydantic support
- **TTL**: Based on volatility (user profile 1h, suggestions 4h)
- **Error Handling**: Graceful degradation (continue on cache failure)

---

## CQRS & Event Bus

### PyMediator Event Bus

**Architecture**:
- **Singleton Registry**: Prevents memory leaks from dynamic class generation
- **Request-Scoped Sessions**: Handlers use request-scoped DB sessions
- **Async Execution**: Direct async handler invocation, background tasks for events

**Two Event Buses**:
1. **Food Search Bus**: Lightweight, food queries only (no heavy services)
2. **Configured Bus**: Full CQRS with all handlers

**Usage**:
```python
# Commands/Queries (synchronous)
result = await event_bus.send(CreateMealCommand(...))

# Domain Events (asynchronous, fire-and-forget)
await event_bus.publish(MealCreatedEvent(...))
```

**Handler Registration**:
```python
@handles(CreateMealCommand)
class CreateMealCommandHandler(EventHandler):
    async def handle(self, command: CreateMealCommand) -> Meal:
        # Execute business logic
        pass
```

---

## Database Architecture

### Schema Design

**Core Tables**:
- **users**: Firebase UID mapping, OAuth provider, timezone, onboarding status
- **user_profiles**: Physical attributes (age, gender, height, weight, body fat), goals (activity level, fitness goal, target weight), preferences (dietary, allergies, health conditions)
- **subscriptions**: RevenueCat integration cache (product_id, platform, status, timestamps)
- **meal**: Primary meal record (status state machine, dish_name, ready_at, error_message, edit tracking)
- **mealimage**: Cloudinary references (url, format, size, width, height)
- **nutrition**: Macros + confidence score (calories, protein, carbs, fat, confidence_score)
- **food_item**: Ingredient details (name, quantity, unit, macros, fdc_id, is_custom)
- **meal_plans**: User preferences for plan generation (dietary, allergies, cooking time, fitness goal)
- **notification_preferences**: User notification settings (toggles, timing, intervals)
- **user_fcm_tokens**: Firebase Cloud Messaging tokens (multi-device support)
- **chat_threads**, **chat_messages**: Conversation storage

**Model Mixins**:
- **PrimaryEntityMixin**: GUID primary key (String(36)), created_at, updated_at
- **SecondaryEntityMixin**: Auto-increment integer ID, timestamps
- **TimestampMixin**: Only timestamps (no ID)

**Relationships**:
- User (1:N) UserProfile, Subscription, Meal, NotificationPreferences, UserFcmToken
- Meal (1:1) MealImage, Nutrition
- Nutrition (1:N) FoodItem
- MealPlan (1:N) MealPlanDay (1:N) PlannedMeal

**State Machine** (Meal Status):
```
PROCESSING → ANALYZING → ENRICHING → READY
                                    ↓
                                  FAILED
                                    ↓
                                 INACTIVE
```

---

## External Integrations

### Firebase
**Purpose**: Authentication + Push Notifications

**Auth**:
- Firebase Admin SDK for JWT verification
- Dev bypass middleware for local development
- Token expiration and revocation checks

**FCM**:
- Platform-specific configs (Android high priority, APNS alert/badge/sound)
- Multi-device support via user_fcm_tokens table
- Failed token tracking with error codes

### Cloudinary
**Purpose**: Image Storage

**Features**:
- Folder organization ("mealtrack")
- Secure URL generation
- Format support (JPEG, PNG)
- Resource API with fallback to direct URL construction

### Google Gemini
**Purpose**: AI Meal Analysis + Chat

**Multi-Model Strategy** (Rate Distribution):
- **MEAL_NAMES**: gemini-2.5-flash-lite (10 RPM)
- **RECIPE_PRIMARY**: gemini-2.5-flash (5 RPM)
- **RECIPE_SECONDARY**: gemini-3-flash (load distribution)
- **GENERAL**: Default fallback

**Vision AI**:
- 6 analysis strategies (basic, portion, ingredient, weight, user-context, combined)
- JSON parsing with multiple fallbacks (direct, markdown extraction, regex, truncation recovery)
- Safety detection (blocked responses)

**Token Optimization**:
- Weekly plans: 8000 tokens
- Meal suggestions: 1500 * count (max 8000)
- Daily multi-meal: 3000 tokens
- Single meal: 1500 tokens

### Pinecone
**Purpose**: Vector Search for Ingredient Nutrition

**Configuration**:
- **Embedding Model**: llama-text-embed-v2 (1024 dimensions)
- **Indexes**: "ingredients", "usda"
- **Similarity Threshold**: 0.35

**Features**:
- Semantic ingredient search
- Nutrition scaling by portion
- Unit conversion (g, kg, oz, lb, ml, cup, tbsp, tsp, etc.)
- Aggregate nutrition calculation

### RevenueCat
**Purpose**: Subscription Management

**Features**:
- Webhook sync to local DB (subscriptions table)
- Premium status check with cache fallback
- Signature verification for webhooks

---

## Security Architecture

### Authentication Flow
```
1. Client sends Firebase ID token in Authorization header
2. verify_firebase_token() validates via Firebase Admin SDK
3. get_current_user_id() maps Firebase UID to database UUID
4. Checks user.is_active (blocks inactive/deleted users)
5. Returns UUID user_id for use in handlers
```

### Authorization
- **User Ownership**: All queries/commands verify user_id matching
- **Premium Features**: `require_premium()` dependency (TODO: apply to routes)
- **Webhook Auth**: RevenueCat signature verification

### Input Validation
- **Pydantic Schemas**: Type validation, required fields, constraints
- **File Uploads**: Max 10MB, content type validation (image/jpeg, image/png)
- **User Input Sanitization**: Prevent prompt injection in descriptions

### Data Protection
- **Soft Deletes**: Meals marked INACTIVE instead of deleted
- **Request Isolation**: Request-scoped DB sessions prevent data leaks
- **Secrets Management**: Environment variables via .env

---

## Performance & Scalability

### Database Optimization
- **Eager Loading**: Pre-defined load options for consistent performance
- **Connection Pooling**: Dynamic sizing based on worker count
- **Indexes**: Firebase UID, status, dates, user_id foreign keys

### Caching Strategy
- **Cache-Aside Pattern**: Check cache → miss → fetch from DB → populate cache
- **TTL by Volatility**: User profile 1h, suggestions 4h, TDEE calculations 1h
- **Graceful Degradation**: Continue on cache failure

### Event Bus
- **Singleton Pattern**: Reuse event bus instance across requests
- **Request-Scoped Sessions**: Handlers get fresh DB sessions per request
- **Background Events**: Non-blocking async processing

### API Performance
- **Request ID Tracking**: X-Request-ID header for tracing
- **Slow Request Detection**: Warns on >1s requests
- **Response Time Header**: X-Response-Time for monitoring

---

## Deployment Architecture

### Environment Configuration
- **Development**: Dev auth bypass, mock storage, verbose logging
- **Production**: Firebase JWT required, external storage, structured logging

### Lifecycle Management
**Startup**:
1. Initialize Firebase Admin SDK (3 methods: file path, JSON string, default credentials)
2. Run Alembic database migrations (with retry logic)
3. Start scheduled notification service
4. Initialize Redis cache layer

**Shutdown**:
1. Stop scheduled notification service
2. Disconnect Redis cache

**Error Handling**:
- `FAIL_ON_MIGRATION_ERROR=true` → Exit if migrations fail
- `FAIL_ON_CACHE_ERROR=true` → Exit if cache init fails
- Otherwise: Log errors and continue (degraded mode)

### Health Checks
- `/health` - Basic health check
- `/health/db-pool` - DB pool metrics
- `/health/mysql-connections` - MySQL connection stats
- `/health/notifications` - FCM health

---

## Architectural Strengths

1. **Clear Separation of Concerns**: 4 distinct layers with well-defined responsibilities
2. **CQRS Flexibility**: Independent scaling of read/write operations
3. **Event-Driven Scalability**: Async background processing for long-running tasks
4. **Dependency Inversion**: Domain layer has zero infrastructure dependencies
5. **Testability**: Isolated handlers with injected dependencies (681+ tests, 70%+ coverage)
6. **Strategy Pattern**: Flexible meal analysis with pluggable strategies
7. **Multi-Model AI**: Rate limit distribution across Gemini models
8. **Graceful Degradation**: Cache and external service failures handled gracefully

---

## Known Issues & Technical Debt

1. **CORS Wide Open**: `allow_origins=["*"]` in production (security risk)
2. **Daily Meals Router Commented Out**: Line 207 in main.py
3. **Premium Features Not Restricted**: No routes use `require_premium` dependency
4. **Hardcoded Values**: MAX_FILE_SIZE, SLOW_REQUEST_THRESHOLD not in config
5. **No Rate Limiting**: AI-heavy endpoints lack rate limits
6. **No API Versioning Strategy**: Only v1 exists, no migration plan
7. **CloudinaryImageStore Instantiation**: Created directly in routes instead of DI
8. **Dev Meal Seeding**: May clutter DB in long-running dev environments

---

**Source**: Scout analysis of 408 files (~37K LOC) conducted January 16, 2026.
