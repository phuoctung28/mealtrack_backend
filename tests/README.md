# Testing Strategy

This document outlines the testing approach for the MealTrack application.

## Test Structure

```
tests/
├── conftest.py          # Global fixtures and configuration
├── fixtures/            # Test data factories and builders
│   └── factories.py     # Factory classes for test objects
├── unit/                # Unit tests (fast, isolated)
│   ├── test_meal_command_handlers.py
│   ├── test_user_command_handlers.py
│   └── test_daily_meal_command_handlers.py
└── integration/         # Integration tests (with database)
    ├── test_meal_query_handlers.py
    ├── test_user_query_handlers.py
    └── test_event_driven_flow.py
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Test individual handlers in isolation
- Use mock services (MockImageStore, MockVisionAIService)
- No external dependencies
- Fast execution

### Integration Tests (`@pytest.mark.integration`)
- Test handler interactions with database
- Test complete workflows
- Use test database with rollback
- Slower but more comprehensive

### API Tests (`@pytest.mark.api`)
- Test HTTP endpoints
- Require running server
- Full request/response cycle

## Key Testing Features

### 1. Database Isolation
- Each test runs in a transaction that's rolled back
- No test data pollution between tests
- SQLite in-memory database for speed

### 2. Mock Services
- `MockImageStore`: In-memory image storage
- `MockVisionAIService`: Returns consistent test data
- `MockMealSuggestionService`: Generates test meal suggestions

### 3. Test Data Factories
- `UserFactory`: Creates test users
- `MealFactory`: Creates test meals
- `TestDataBuilder`: Complex test scenarios

### 4. Event Bus Testing
- All handlers registered in test configuration
- Tests use event bus to simulate real application flow
- Proper command/query separation

## Running Tests

### Quick Commands
```bash
# Quick health check
python run_tests.py health

# Run fast tests
python run_tests.py fast

# Run unit tests
python run_tests.py unit

# Run with coverage
python run_tests.py coverage

# Run all tests
python run_tests.py all
```

### Direct pytest Usage
```bash
# Run specific test file
pytest tests/unit/test_meal_command_handlers.py

# Run specific test
pytest tests/unit/test_meal_command_handlers.py::TestUploadMealImageCommandHandler::test_upload_meal_image_success

# Run with markers
pytest -m unit
pytest -m "unit and not slow"

# Run with coverage
pytest --cov=src --cov-report=html
```

## CI/CD Integration

GitHub Actions workflow (`.github/workflows/test.yml`):
1. Sets up Python environment
2. Installs dependencies
3. Runs unit tests
4. Runs integration tests
5. Generates coverage reports
6. Runs linting and security checks

## Best Practices

1. **Test Naming**: Use descriptive names that explain what's being tested
   - Good: `test_upload_meal_image_stores_meal_in_repository`
   - Bad: `test_upload`

2. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   # Arrange
   command = UploadMealImageCommand(...)
   
   # Act
   result = await event_bus.send(command)
   
   # Assert
   assert result["status"] == "processing"
   ```

3. **Test Data**: Use factories for consistent test data
   ```python
   meal, food_items = test_data_builder.create_meal_with_food_items()
   ```

4. **Error Cases**: Always test error scenarios
   ```python
   with pytest.raises(ValidationException):
       await event_bus.send(invalid_command)
   ```

5. **Async Testing**: Use `pytest-asyncio` for async handlers
   ```python
   async def test_async_handler(event_bus):
       result = await event_bus.send(command)
   ```

## Coverage Goals

- Unit test coverage: > 80%
- Integration test coverage: > 70%
- Overall coverage: > 75%

## Debugging Tests

1. **Verbose Output**: `pytest -vv`
2. **Show Print Statements**: `pytest -s`
3. **Stop on First Failure**: `pytest -x`
4. **Debug with pdb**: `pytest --pdb`
5. **Test Specific Pattern**: `pytest -k "meal"`

## Adding New Tests

1. Identify the handler/component to test
2. Choose appropriate test type (unit/integration)
3. Create test file in correct directory
4. Use appropriate fixtures and mocks
5. Test both success and error cases
6. Run tests locally before committing
7. Ensure CI passes