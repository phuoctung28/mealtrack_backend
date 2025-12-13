# Backend API - Claude Code Context

## Quick Reference

| Item | Value |
|------|-------|
| **Framework** | FastAPI 0.115+ / Python 3.11+ |
| **Database** | MySQL 8.0 + SQLAlchemy 2.0 |
| **Migrations** | Alembic |
| **Architecture** | 4-layer Clean + CQRS |
| **Event Bus** | PyMediator |
| **AI** | Google Gemini via LangChain |
| **Auth** | Firebase JWT |

## Architecture

```
src/
├── api/              # Presentation Layer
│   ├── routes/v1/    # REST endpoints
│   ├── schemas/      # Pydantic request/response
│   ├── dependencies/ # FastAPI DI (auth, event_bus)
│   ├── middleware/   # Auth bypass, premium check
│   └── mappers/      # API <-> Domain mapping
│
├── app/              # Application Layer (CQRS)
│   ├── commands/     # Write operations
│   ├── queries/      # Read operations
│   ├── events/       # Domain events
│   └── handlers/     # Command/Query/Event handlers
│
├── domain/           # Business Logic Layer
│   ├── model/        # Domain entities
│   ├── services/     # Domain services
│   ├── ports/        # Interfaces (dependency inversion)
│   └── prompts/      # AI prompt templates
│
└── infra/            # Infrastructure Layer
    ├── database/     # SQLAlchemy models, config
    ├── repositories/ # Data access implementations
    ├── adapters/     # External service integrations
    ├── services/     # Firebase, Pinecone, etc.
    └── event_bus/    # PyMediator implementation
```

## CQRS Pattern

### Commands (Write)
```python
# src/app/commands/meal/create_meal_command.py
@dataclass
class CreateMealCommand:
    user_id: str
    image_data: bytes

# src/app/handlers/command_handlers/meal_command_handlers.py
class CreateMealCommandHandler:
    async def handle(self, command: CreateMealCommand) -> Meal:
        # Business logic here
```

### Queries (Read)
```python
# src/app/queries/meal/get_meal_query.py
@dataclass
class GetMealQuery:
    meal_id: str
    user_id: str
```

### Events
```python
# src/app/events/meal/meal_created_event.py
@dataclass
class MealCreatedEvent:
    meal_id: str
    user_id: str
    created_at: datetime
```

## Critical Commands

```bash
# Run development server
uvicorn src.api.main:app --reload

# Database migrations
alembic upgrade head           # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Code quality
black src/ tests/              # Format
flake8 src/ tests/             # Lint
mypy src/                      # Type check
pytest                         # Test

# Full check before commit
black src/ tests/ && flake8 && mypy src/ && pytest
```

## API Endpoints

Base URL: `http://localhost:8000`
Docs: `http://localhost:8000/docs`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/meals/image` | Analyze meal image |
| GET | `/v1/meals/{id}` | Get meal details |
| PUT | `/v1/meals/{id}` | Update meal |
| DELETE | `/v1/meals/{id}` | Delete meal |
| GET | `/v1/daily-meals` | Daily suggestions |
| POST | `/v1/meal-plans/weekly` | Generate weekly plan |
| GET | `/v1/user-profiles/me` | User profile |
| PUT | `/v1/user-profiles/me` | Update profile |

## Database

### Models Location
`src/infra/database/models/`

### Key Tables
- `users` - Firebase UID mapping
- `profiles` - User health metrics
- `meals` - Meal records
- `meal_images` - Cloudinary refs
- `nutrition` - Macro/micro data
- `food_items` - Ingredients
- `meal_plans` - Weekly plans
- `subscriptions` - RevenueCat sync
- `notification_preferences` - FCM settings

### Migration Workflow
```bash
# Create new migration
alembic revision --autogenerate -m "add_column_to_users"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Dependency Injection

FastAPI Depends pattern:

```python
# In route
@router.get("/meals/{id}")
async def get_meal(
    id: str,
    current_user: User = Depends(get_current_user),
    event_bus: EventBus = Depends(get_event_bus),
):
    ...
```

## External Services

| Service | Purpose | Config |
|---------|---------|--------|
| Firebase | Auth + FCM | `FIREBASE_CREDENTIALS` |
| Cloudinary | Image storage | `CLOUDINARY_*` |
| Google Gemini | AI meal analysis | `GOOGLE_API_KEY` |
| Pinecone | Vector search | `PINECONE_*` |
| MySQL | Primary DB | `DATABASE_URL` |
| Redis | Caching | `REDIS_URL` |

## Domain Services

Key business logic in `src/domain/services/`:

- `meal_service.py` - Core meal operations
- `tdee_service.py` - TDEE calculation
- `nutrition_calculation_service.py` - Macro aggregation
- `meal_plan_service.py` - Plan generation
- `notification_service.py` - FCM orchestration

## Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Unit only
pytest -m unit

# Integration only
pytest -m integration

# Specific file
pytest tests/unit/domain/services/test_meal_service.py
```

## Environment Variables

Required in `.env`:
```
DATABASE_URL=mysql+pymysql://user:pass@host/db
GOOGLE_API_KEY=...
FIREBASE_CREDENTIALS=path/to/credentials.json
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

## Common Gotchas

1. **Import errors** → Check `__init__.py` exports
2. **DB connection** → Verify DATABASE_URL format
3. **Migration conflict** → `alembic heads` to check branches
4. **Auth fails** → Check Firebase credentials path
5. **Type errors** → Run `mypy src/` before commit

## File Naming

- `snake_case.py` for all files
- `*_service.py` for services
- `*_repository.py` for repositories
- `*_handler.py` for CQRS handlers
- `*_command.py`, `*_query.py`, `*_event.py` for CQRS

## Key Files

| Purpose | File |
|---------|------|
| App Entry | `src/api/main.py` |
| Routes | `src/api/routes/v1/` |
| DB Config | `src/infra/database/config.py` |
| Settings | `src/infra/config/settings.py` |
| Auth | `src/api/dependencies/auth.py` |
