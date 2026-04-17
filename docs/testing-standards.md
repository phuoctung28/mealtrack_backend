# Backend Testing Standards

**Last Updated:** April 17, 2026  
**Coverage Target:** 70%+ overall, 100% critical paths, 80%+ new features  
**Total Tests:** 681+ tests in 92 test files

---

## Test Organization

```
tests/
├── unit/
│   ├── domain/          # Domain services, entities
│   ├── app/             # Handlers, commands, queries
│   └── conftest.py      # Shared fixtures
└── integration/
    ├── api/             # Route endpoints
    ├── infra/           # Repository, external services
    └── conftest.py      # DB/event bus fixtures
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
    command = CreateMealCommand(user_id=user.id, ...)
    
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
pytest -m integration               # Integration tests only
pytest --cov=src --cov-report=html  # With coverage report
```

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

Place in `conftest.py`:

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

For integration tests with DB access:

```python
@pytest.mark.integration
def test_meal_repository_find_by_id_performance(benchmark):
    result = benchmark(repo.find_by_id, "meal-1")
    assert result is not None
```

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
