# MealTrack Backend - Code Standards

**Last Updated:** April 17, 2026
**Version:** 0.6.1
**Applies To:** All code in `src/` (430 files, ~38.5K LOC: API 76, App 140, Domain 133, Infra 80)

---

## File Naming Conventions

### All Files
- Use `snake_case.py` for all Python files.
- Descriptive names that indicate purpose (prefer longer, clearer names over abbreviations).

### Pattern-Based Naming
- Commands: `*_command.py` (e.g., `create_meal_command.py`)
- Queries: `*_query.py` (e.g., `get_meal_by_id_query.py`)
- Events: `*_event.py` (e.g., `meal_created_event.py`)
- Handlers: `*_handler.py` (e.g., `create_meal_command_handler.py`)
- Services: `*_service.py` (e.g., `tdee_service.py`)
- Repositories: `*_repository.py` (e.g., `meal_repository.py`)
- Ports: `*_port.py` (e.g., `meal_repository_port.py`)

---

## File Size Limits

- **Target**: <200 LOC per file for optimal readability.
- **Maximum**: 400 LOC absolute limit.
- **When Exceeding**:
  - Split into smaller, focused modules.
  - Extract utility functions into separate files.
  - Use composition over inheritance for complex classes.

---

## Architecture Layers

### 1. API Layer (`src/api/`)
**Purpose**: HTTP presentation layer

**Responsibilities**:
- Handle HTTP requests/responses
- Validate input via Pydantic schemas
- Dispatch commands/queries to event bus
- Map domain models to response DTOs
- Handle authentication/authorization

**Patterns**:
```python
# Route example
@router.post("/meals/image/analyze")
async def analyze_meal_image(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    event_bus: EventBus = Depends(get_event_bus),
):
    # 1. Validate request
    # 2. Create command
    # 3. Dispatch to event bus
    # 4. Map to response DTO
    # 5. Return response
```

**Key Files**:
- `main.py`: FastAPI app initialization (228 LOC)
- `routes/v1/*`: 12 route modules with 50+ endpoints
- `schemas/*`: 34 Pydantic request/response models
- `mappers/*`: 8 API ↔ Domain mappers
- `dependencies/*`: Auth (Firebase JWT) and event bus (PyMediator singleton) DI
- `middleware/*`: 3-layer middleware stack (CORS, logging, dev auth bypass)
- `exceptions.py`: 7 custom exception types

### 2. Application Layer (`src/app/`)
**Purpose**: CQRS implementation

**Responsibilities**:
- Execute commands (write operations)
- Execute queries (read operations)
- Publish domain events
- Coordinate application services

**Patterns**:
```python
# Command example
@dataclass
class CreateMealCommand(Command):
    user_id: str
    image_data: bytes

    def __post_init__(self):
        # Validation logic
        pass

# Handler example
@handles(CreateMealCommand)
class CreateMealCommandHandler(EventHandler[CreateMealCommand, Meal]):
    def __init__(self, meal_repo: MealRepositoryPort):
        self.meal_repo = meal_repo

    async def handle(self, command: CreateMealCommand) -> Meal:
        # Execute business logic
        # Return result
        pass
```

**Key Files**:
- `commands/*`: 30 command definitions across 11 domains (Chat, Meal, Daily Meal, Meal Plan, Meal Suggestion, User, Notification, Ingredient, TDEE, Activity, Food)
- `queries/*`: 31 query definitions
- `events/*`: 19 domain events
- `handlers/*`: 54 handlers with @handles decorator
- `services/chat/*`: 3 application services (MessageOrchestrationService, AIResponseCoordinator, ChatNotificationService)

### 3. Domain Layer (`src/domain/`)
**Purpose**: Core business logic (zero external dependencies)

**Responsibilities**:
- Domain models with business rules
- Domain services (business logic)
- Port interfaces (dependency inversion)
- Business constants and rules
- AI prompt templates

**Patterns**:
```python
# Domain entity
@dataclass
class Meal:
    meal_id: str
    user_id: str
    status: MealStatus
    nutrition: Optional[Nutrition] = None

    def __post_init__(self):
        # Validate domain invariants
        pass

    def mark_ready(self):
        # Business logic method
        self.status = MealStatus.READY

# Domain service
class TdeeCalculationService:
    def calculate_tdee(self, request: TdeeRequest) -> TdeeResponse:
        # Auto-select formula
        # Calculate BMR, TDEE, macros
        # Return result with metadata
        pass
```

**Key Files**:
- `model/*`: 30+ domain entities in 8 bounded contexts (Meal aggregate with state machine: PROCESSING → ANALYZING → ENRICHING → READY/FAILED/INACTIVE), 44 files, 3,544 LOC
- `services/*`: 50+ domain services including TDEE calculation (BMR formulas: Mifflin-St Jeor, Katch-McArdle), nutrition aggregation, meal planning, ~7,924 LOC
- `ports/*`: 17 port interfaces for dependency inversion
- `strategies/*`: 6 meal analysis strategies (Strategy Pattern)
- `prompts/*`: 4 AI prompt templates
- `constants/*`: Business constants (TDEE, nutrition, meal distribution)

### 4. Infrastructure Layer (`src/infra/`)
**Purpose**: Technical implementation details

**Responsibilities**:
- Database persistence (SQLAlchemy + Alembic)
- External service adapters
- Caching (Redis)
- Event bus implementation (PyMediator)
- Configuration management

**Patterns**:
```python
# Repository implementation
class MealRepository(MealRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    def save(self, meal: Meal) -> Meal:
        # Smart sync with diff-based updates
        # Eager load relationships
        # Return persisted meal
        pass

# Service adapter
class VisionAIService(VisionAIServicePort):
    def __init__(self, model_manager: GeminiModelManager):
        self.model_manager = model_manager

    async def analyze(self, image_bytes: bytes) -> str:
        # Call external AI service
        # Parse response
        # Return JSON string
        pass
```

**Key Files**:
- `database/models/*`: 13+ core database tables with connection pooling (20 connections + 10 overflow)
- `repositories/*`: 10+ repository implementations with smart sync and eager loading
- `adapters/*`: Vision AI, Meal Generation (multi-model Gemini), Cloudinary, Unsplash/Pexels (meal discovery)
- `services/*`: Firebase (FCM), Pinecone (1024-dim vector search)
- `cache/*`: Redis cache-aside pattern (50 connections, 1h default TTL, graceful degradation)
- `event_bus/*`: PyMediator with singleton registry and async execution
- `websocket/*`: ConnectionManager for real-time chat
- `monitoring/*`: Sentry SDK integration (error tracking, performance monitoring)

---

## CQRS Patterns

### Commands (Write Operations)
```python
@dataclass
class UpdateUserMetricsCommand(Command):
    user_id: str
    weight_kg: float
    body_fat_percentage: Optional[float] = None

    def __post_init__(self):
        if self.weight_kg <= 0:
            raise ValidationException("Weight must be positive")
```

**Naming**: Imperative verbs (Create, Update, Delete, Generate, Register)

**Validation**: In `__post_init__()` method

**Return**: Domain entity or None

### Queries (Read Operations)
```python
@dataclass
class GetMealByIdQuery(Query):
    meal_id: str
    user_id: str
```

**Naming**: Start with "Get" or "Search"

**Validation**: Optional (simple validation only)

**Return**: Domain entity, list, or DTO

### Events (Domain Events)
```python
@dataclass
class MealCreatedEvent(DomainEvent):
    aggregate_id: str  # Meal ID
    meal_id: str
    user_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
```

**Naming**: Past tense (Created, Updated, Deleted, Generated)

**Metadata**: Always include `event_id`, `timestamp`, optional `correlation_id`

**Purpose**: Historical facts, not commands

---

## Dependency Injection

### FastAPI Dependencies
```python
# In dependencies/auth.py
def get_current_user(
    authorization: str = Header(None),
) -> User:
    # Verify Firebase JWT
    # Return user
    pass

# In route
@router.get("/meals/{id}")
async def get_meal(
    id: str,
    current_user: User = Depends(get_current_user),
):
    # Use current_user
    pass
```

### Handler Dependencies
```python
class CreateMealCommandHandler:
    def __init__(
        self,
        meal_repo: MealRepositoryPort,
        image_store: ImageStorePort,
    ):
        self.meal_repo = meal_repo
        self.image_store = image_store

    def set_dependencies(self, **kwargs):
        # Runtime dependency injection
        self.meal_repo = kwargs.get('meal_repo', self.meal_repo)
```

---

## Database Patterns

### Model Conventions
```python
class Meal(PrimaryEntityMixin, Base):
    __tablename__ = "meal"

    # Relationships with eager loading
    image = relationship("MealImage", lazy="joined")
    nutrition = relationship("Nutrition", lazy="joined")

    # Domain conversion
    def to_domain(self) -> DomainMeal:
        # Map DB model to domain entity
        pass

    @staticmethod
    def from_domain(meal: DomainMeal) -> "Meal":
        # Map domain entity to DB model
        pass
```

### Repository Patterns
```python
class MealRepository:
    # Eager loading options (reusable)
    _load_options = [
        joinedload(MealModel.image),
        joinedload(MealModel.nutrition).joinedload(Nutrition.food_items),
    ]

    def find_by_id(self, meal_id: str) -> Optional[Meal]:
        db_meal = self.session.query(MealModel).options(
            *self._load_options
        ).filter_by(meal_id=meal_id).first()

        return db_meal.to_domain() if db_meal else None

    def save(self, meal: Meal) -> Meal:
        # Smart sync: update existing or create new
        # Diff-based updates for nested entities
        pass
```

---

## Error Handling

### Exception Hierarchy
```
MealTrackException (base)
├── ValidationException → 400
├── ResourceNotFoundException → 404
├── BusinessLogicException → 422
├── ConflictException → 409
├── ExternalServiceException → 503
├── AuthenticationException → 401
└── AuthorizationException → 403
```

### Usage in Handlers
```python
async def handle(self, query: GetMealByIdQuery) -> Meal:
    meal = self.meal_repo.find_by_id(query.meal_id)
    if not meal:
        raise ResourceNotFoundException(
            message=f"Meal {query.meal_id} not found",
            error_code="MEAL_NOT_FOUND",
            details={"meal_id": query.meal_id}
        )
    return meal
```

---

## Testing Standards

### Test Organization
```
tests/
├── unit/                    # Domain/app logic
│   ├── domain/
│   └── app/
└── integration/             # API/infra
    ├── api/
    └── infra/
```

### Test Naming
```python
def test_tdee_calculation_with_body_fat_uses_katch_mcardle():
    # Test name describes: what + condition + expected result
    pass
```

### Coverage Requirements
- Overall: 70%+
- Critical paths: 100%
- New features: 80%+

---

## Code Quality

### Type Hints
```python
# Required for all function signatures
def calculate_tdee(
    request: TdeeRequest,
    formula: Optional[str] = None,
) -> TdeeResponse:
    pass
```

### Dataclasses
```python
# Prefer dataclasses for DTOs and value objects
@dataclass
class Nutrition:
    calories: float
    protein: float
    carbs: float
    fat: float
    confidence_score: float = 0.0

    def __post_init__(self):
        # Validation
        if self.calories < 0:
            raise ValueError("Calories cannot be negative")
```

### Enums
```python
# Use enums for constrained values
class MealStatus(str, Enum):
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"
```

---

## Performance Best Practices

### Database
- Use eager loading for known relationships
- Request-scoped sessions (no global session)
- Connection pool sizing based on worker count

### Caching
- Redis cache-aside pattern
- Graceful degradation (continue on cache failure)
- TTL based on data volatility (user profile: 1h, suggestions: 4h)

### Event Bus
- Singleton registry pattern to prevent memory leaks from dynamic class generation
- Request-scoped sessions for handlers
- Background event processing (non-blocking)
- Async handlers for I/O-bound operations with @handles decorator
- Two event buses: Food Search Bus (lightweight) and Configured Bus (full CQRS)

---

## Security Standards

### Authentication
- Firebase JWT verification on all protected endpoints
- Dev bypass middleware for local development only
- Token expiration and revocation checks

### Input Validation
- Pydantic schemas for all API inputs
- File size limits (10MB for images)
- Content type validation
- User input sanitization (prevent prompt injection)

### Authorization
- User ownership checks (user_id matching)
- Premium feature gates via `require_premium` dependency
- RevenueCat webhook signature verification

---

## Business Rules Documentation

### Calorie Derivation (SINGLE SOURCE OF TRUTH - Mar 2026)
```python
# **Backend-derived formula (macros are source of truth)**
# Fiber-aware: P*4 + (C-fiber)*4 + fiber*2 + F*9
# Mobile receives all calorie values from backend; does not re-derive

net_carbs = carbs - fiber
calories = protein*4 + net_carbs*4 + fiber*2 + fat*9
# Result kept to 1 decimal place in backend; mobile rounds for display
```

### Macro Validation Service (NEW - Mar 2026)
```python
# Post-generation validation for AI macros (MacroValidationService)
# Threshold: 10% divergence between derived and reported calories
# If >10% divergent: trusts macros over reported calories, logs warning

def validate_and_correct(macros: dict) -> dict:
    """Corrects calories if >10% off from fiber-aware formula."""
    net_carbs = max(0, carbs - fiber)
    derived_cal = protein*4 + net_carbs*4 + fiber*2 + fat*9

    diff_pct = abs(derived_cal - reported_cal) / reported_cal * 100
    if diff_pct > 10.0:
        macros["calories"] = derived_cal
        macros["_validation"] = {"corrected": True, "diff_pct": ...}
    return macros
```

### Food Density Conversion (NEW - Mar 2026)
```python
# 30+ food density constants (g/ml) for volume→mass conversion
# Honey 1.42, oil 0.92, milk 1.03, water 1.0, etc.
# File: src/domain/constants/food_density.py
# Applied: NutritionCalculationService.convert_quantity_to_grams(quantity, unit, food_name)
# Default density for unknown liquids: 1.0 (water)
```

### Custom Macro Targets (NEW - Mar 2026)
```python
# Users can override calculated macros per profile
# Fields: custom_protein_g, custom_carbs_g, custom_fat_g (nullable)
# When all three non-null: custom values take precedence
# Migration: 037_add_custom_macro_columns
# Updated via: UpdateCustomMacrosCommand / UpdateCustomMacrosCommandHandler
```

### Weekly Budget & Adjusted Daily Target (Mar 2026)
```python
# Weekly budget stored per user with remaining_days calculation
# remaining_days: Mon=7, Tue=6, ..., Sun=1 (includes today)
# Adjusted daily target = redistributed based on previous days consumption
# Used by: SuggestionOrchestrationService, meal plans, daily targets
# BMR floor = 80% of standard daily (prevents dangerously low)
# Service: WeeklyBudgetService.calculate_adjusted_daily()
```

### TDEE Calculation
```python
# Auto-select formula:
# - Katch-McArdle if body_fat_percentage provided
# - Mifflin-St Jeor otherwise

# Activity multipliers
SEDENTARY = 1.2
LIGHT = 1.375
MODERATE = 1.55
ACTIVE = 1.725
EXTRA = 1.9

# Goal adjustments
CUT = -500  # calories
BULK = +300
RECOMP = 0

# Macro ratios (protein/carbs/fat)
BULK_MACROS = (0.30, 0.45, 0.25)
CUT_MACROS = (0.35, 0.40, 0.25)
RECOMP_MACROS = (0.35, 0.40, 0.25)
```

### Meal Type Determination (Time-Based)
```python
# 05:00-10:30 → Breakfast
# 11:00-14:30 → Lunch
# 17:00-21:00 → Dinner
# Other → Snack
```

### Calorie Distribution
```python
BREAKFAST_PERCENT = 0.25
LUNCH_PERCENT = 0.35
DINNER_PERCENT = 0.30
SNACK_PERCENT = 0.10

# If snacks included: reduce main meals by 10%
MIN_CALORIES_FOR_SNACK = 1800
```

---

## Multi-Language Support

### Language Codes
- Supported: `en`, `vi`, `es`, `fr`, `de`, `ja`, `zh` (ISO 639-1)
- Fallback: English for invalid codes

### Translation Approach
1. AI generates responses in English
2. TranslationService translates to user language post-generation
3. Documented in code comments

---

## Domain Services (Key Files)

### Nutrition & Macros
- `nutrition_calculation_service.py` - Aggregates nutrition from food items, applies density conversion
- `macro_validation_service.py` - Post-generation macro validation (NEW Mar 2026)
- `tdee_service.py` - TDEE calculation with auto-formula selection
- `weekly_budget_service.py` - Weekly budget calculation with adjusted daily targets
- `food_density.py` - 30+ food density constants for ml↔g conversion

### Suggestions & Meal Planning
- `suggestion_orchestration_service.py` - Session-based suggestions with adjusted daily target (updated Mar 2026)
- `meal_plan_service.py` - Meal plan generation and validation
- `portion_calculation_service.py` - Portion multiplier calculations

### Meal Analysis & Processing
- `meal_service.py` - Meal lifecycle management with state machine
- `meal_analysis_strategy.py` - 6 strategies: basic, portion-aware, ingredient-aware, weight-aware, user-context, combined
- `meal_edit_strategies.py` - Post-analysis editing strategies

### AI & External Integration
- `meal_generation_service.py` - Multi-model Gemini for meal generation
- `translation_service.py` - Multi-language support (7 languages)
- `notification_service.py` - FCM push notifications with deduplication (migration 047)
- `conversation_service.py` - Conversation state management
- `meal_discovery/` - Meal discovery service with image search (Unsplash, Pexels adapters)

---

## Migration History (Recent)

| Version | Changes |
|---------|---------|
| 047 | Add notification_sent_log table for cross-worker deduplication (Apr 2026) |
| 046 | Add name_normalized to food_reference (Apr 2026) |
| 045 | Add challenge_duration, training_types to user_profiles — onboarding redesign (Apr 2026) |
| 044 | Widen firebase_uid to 128 chars (Mar 2026) |
| 043 | Add language_code to users (Mar 2026) |
| 037 | Add custom_protein_g, custom_carbs_g, custom_fat_g to user_profiles |
| 036 | Add date_of_birth to user_profiles |
| 035 | Evolve barcode_products → food_reference (food data evolution) |
| 034 | Add fiber, sugar columns to food_item and nutrition tables |

---

## New Features (Apr 2026)

### Sentry Monitoring
- Error tracking and performance monitoring integration
- FastAPI, Starlette, SQLAlchemy middleware integrations
- Configurable via `SENTRY_DSN`, traces/profile sample rates
- Gracefully disabled if DSN not set

### Meal Discovery
- Endpoint: `POST /v1/meal-suggestions/discover` — 6 meals per batch
- Integrates image search (Unsplash, Pexels adapters)
- Food image validation for quality control
- Returns meal options with images for visual selection

### Notification Deduplication
- Migration 047: `notification_sent_log` table with composite key (user_id, notification_type, sent_minute)
- Prevents duplicate FCM sends across worker processes
- Indexed on sent_at for efficient cleanup

### Onboarding Redesign (Migration 045)
- New fields: `challenge_duration` (string), `training_types` (JSON)
- Enables more granular fitness goal tracking
- Backward compatible (nullable fields)

## Unresolved Questions

1. Should we enforce stricter file size limits (<200 LOC)?
2. Premium feature restrictions not applied - intentional?
3. API versioning strategy needed for v2+?
4. CORS production configuration - when to restrict?
5. Food reference table evolution - timeline for deprecating dual lookup?
6. Rate limit tuning for meal_suggestions endpoints?

## WebSocket Standards

### Connection Management
```python
# ConnectionManager for real-time chat
class ConnectionManager:
    async def connect(self, websocket: WebSocket, user_id: str):
        # Accept and store connection
        pass

    async def disconnect(self, user_id: str):
        # Remove connection
        pass

    async def send_message(self, user_id: str, message: dict):
        # Send to specific user
        pass
```

### Chat Flow
- WebSocket connects via `/v1/chat/ws`
- MessageOrchestrationService coordinates message flow
- AIResponseCoordinator handles streaming AI responses
- ChatNotificationService broadcasts FCM notifications

---

## Async Patterns

### Handler Pattern
```python
@handles(CreateMealCommand)
class CreateMealCommandHandler:
    async def handle(self, command: CreateMealCommand) -> Meal:
        # Async business logic
        pass
```

### Event Publishing
```python
# Fire-and-forget domain events
await event_bus.publish(MealCreatedEvent(...))

# Synchronous commands/queries
result = await event_bus.send(CreateMealCommand(...))
```

---

**Note**: This document consolidates patterns from 417 source files analyzed via scout reports (Jan 16, 2026).
