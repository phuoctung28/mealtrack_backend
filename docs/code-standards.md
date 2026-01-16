# MealTrack Backend - Code Standards

**Last Updated:** January 16, 2026
**Applies To:** All code in `src/` (408 files, ~37K LOC)

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
- `routes/v1/*`: 14 route modules with 80+ endpoints
- `schemas/*`: 34 Pydantic request/response models
- `mappers/*`: 8 API ↔ Domain mappers
- `dependencies/*`: Auth and event bus DI
- `middleware/*`: 3-layer middleware stack

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
- `commands/*`: 21 command definitions (596 LOC)
- `queries/*`: 20 query definitions (359 LOC)
- `events/*`: 11+ domain events (448 LOC)
- `handlers/*`: 49 handlers (31 command, 18 query, 1 event)

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
- `model/*`: 44 domain entities in 8 bounded contexts
- `services/*`: 50 domain services (7,924 LOC)
- `ports/*`: 15 port interfaces for dependency inversion
- `strategies/*`: 6 analysis strategies
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
- `database/models/*`: 11 main database tables
- `repositories/*`: 10+ repository implementations
- `adapters/*`: Vision AI, Meal Generation, Cloudinary
- `services/*`: Firebase, Pinecone integrations
- `cache/*`: Redis caching with graceful degradation
- `event_bus/*`: PyMediator implementation

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
- Singleton event bus with request-scoped sessions
- Background event processing (non-blocking)
- Async handlers for I/O-bound operations

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

## Unresolved Questions

1. Should we enforce stricter file size limits (<200 LOC)?
2. Premium feature restrictions not applied - intentional?
3. API versioning strategy needed for v2+?
4. Rate limiting thresholds for AI endpoints?
5. CORS production configuration - when to restrict?

---

**Note**: This document consolidates patterns from 408 source files analyzed via scout reports (Jan 16, 2026).
