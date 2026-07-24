# Backend Testing Standards

**Last Updated:** July 5, 2026
**Coverage Target:** CI gate 65% for unit coverage; docs target 70%+ overall, 100% critical paths, 80%+ new features
**Suite Size:** 312 Python files in `tests/`; latest collection reaches 1,600+ tests

---

## Test Organization

```
tests/
├── architecture/       # Import boundaries and async-runtime guardrails
├── unit/
│   ├── api/            # Routes, dependencies, middleware, mappers
│   ├── app/            # Handlers, commands, queries, services
│   ├── domain/         # Domain services, entities, policies
│   └── infra/          # Adapters, repositories, event bus, external services
├── integration/
│   ├── api/            # Route endpoints
│   ├── infra/          # Repository, external services
│   ├── postgres/       # Real PostgreSQL catalog/recommendation gates
│   └── routes/         # Route-level integration coverage
├── fixtures/           # Factories, fakes, DB fixtures
└── migrations/         # Alembic migration validation
```

---

## Test Naming Convention

Describe: **what** + **condition** + **expected result**

```python
def test_tdee_calculation_with_body_fat_uses_katch_mcardle():
    pass

def test_meal_type_determined_by_time_returns_breakfast_before_1030():
    pass

def test_repository_find_by_id_raises_not_found_when_missing():
    pass
```

---

## Test Structure

```python
def test_feature_condition_expected():
    # Arrange: set up data
    user = create_test_user()
    command = CreateManualMealCommand(user_id=user.id, ...)
    
    # Act: execute
    meal = await handler.handle(command)
    
    # Assert: verify
    assert meal.status == MealStatus.PROCESSING
    assert meal.user_id == user.id
```

---

## Coverage Requirements

| Category | Minimum | Target |
|----------|---------|--------|
| Overall | 70% | 75%+ |
| Critical paths | 100% | — |
| New features | 80% | 90%+ |
| Domain services | 80%+ | 90%+ |
| Handlers | 75%+ | 85%+ |

---

## Test Markers

```python
import pytest

@pytest.mark.unit
def test_tdee_calculation():
    pass

@pytest.mark.integration
def test_meal_creation_saves_to_db():
    pass
```

**Run specific tests:**
```bash
pytest -m unit                      # Unit tests only
pytest tests/integration -o addopts="" -m integration  # Explicit integration run
TEST_DATABASE_URL=postgresql+asyncpg://nutree:nutree@localhost:5432/nutree_test \
  pytest tests/integration/postgres -o addopts="" -m integration -q
pytest --cov=src --cov-report=html  # With coverage report
```

Default `pytest` uses `pytest.ini` addopts that ignore `tests/integration` and
select `not integration`. CI runs `lint-imports` and then
`pytest tests/unit --cov=src --cov-fail-under=65`.

PostgreSQL integration tests require `TEST_DATABASE_URL` with the
`postgresql+asyncpg://` driver and refuse SQLite or missing URLs. The CI
`postgres-integration` job uses `pgvector/pgvector:pg16`, initializes a fresh
PostgreSQL schema through `scripts/init_postgres_db.py`, then executes only
`tests/integration/postgres`. Use the initializer for empty PostgreSQL
databases because legacy pre-PostgreSQL migration revisions are not replayable
from base. The initializer enables both `vector` and `pg_trgm`; local food
search tests require `pg_trgm` because the repository uses PostgreSQL
`similarity()`.

---

## Mocking Strategy

Mock external services, preserve domain logic:

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_vision_ai():
    return AsyncMock(
        analyze=AsyncMock(
            return_value='{"nutrition": {"calories": 500, ...}}'
        )
    )
```

---

## Fixtures (Reusable)

Place shared fixtures in `tests/conftest.py`; keep domain-specific fixtures in
`tests/fixtures/` or the nearest package-level `conftest.py`:

```python
@pytest.fixture
async def test_user():
    return User(id="test-user", firebase_uid="uid-123")

@pytest.fixture
async def test_meal(test_user):
    return Meal(id="meal-1", user_id=test_user.id, status=MealStatus.READY)

@pytest.fixture
async def event_bus():
    return create_event_bus()
```

---

## Performance Testing

For integration tests with DB access, assert timing directly unless the
`pytest-benchmark` plugin is added to the environment:

```python
@pytest.mark.integration
async def test_meal_repository_find_by_id_performance():
    result = await repo.find_by_id("meal-1")
    assert result is not None
```

Catalog release load gates use Locust:

```bash
MEALTRACK_LOAD_TEST_TOKEN="$TOKEN" \
locust -f tests/performance/locust_meal_catalog.py --headless \
  -u 50 -r 5 --run-time 10m --host "$STAGING_HOST" \
  --csv /tmp/meal-catalog-baseline
```

Do not print bearer tokens or raw response payloads. Commit aggregate CSV
statistics and environment shape only when recording release evidence.

---

## Best Practices

- **Unit tests**: No DB, no external APIs
- **Integration tests**: Use test DB, mock external services
- **Isolation**: Each test is independent
- **Clarity**: Test names describe intent clearly
- **Coverage**: Critical paths at 100%, happy paths at 80%+
- **Async**: Use `async def test_` for async handlers

---

See related: `code-standards.md`, `cqrs-guide.md`
