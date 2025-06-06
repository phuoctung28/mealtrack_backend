# MealTrack API Test Suite

Comprehensive API testing suite for the MealTrack backend, covering all endpoints with functional, performance, and validation tests.

## 🚀 Quick Start

### Prerequisites
1. **API Server Running**: Make sure the MealTrack API server is running on `http://localhost:8000`
2. **Dependencies Installed**: Install testing dependencies
   ```bash
   pip install pytest httpx pytest-html pytest-cov pytest-xdist
   ```

### Run Tests
```bash
# Quick health check
python run_tests.py health

# All tests
python run_tests.py all

# Specific test suites
python run_tests.py api          # API integration tests
python run_tests.py performance  # Performance tests
python run_tests.py validation   # Validation tests
```

## 📁 Test Structure

```
tests/
├── README.md                 # This documentation
├── conftest.py              # Shared fixtures and configuration
├── test_api_endpoints.py    # Main API endpoint tests
├── test_performance.py      # Performance and load tests
└── test_validation.py       # Validation and error handling tests

Root files:
├── run_tests.py             # Test runner script
├── pytest.ini              # Pytest configuration
└── requirements.txt         # Updated with test dependencies
```

## 🧪 Test Categories

### 1. API Endpoint Tests (`test_api_endpoints.py`)

**Comprehensive coverage of all implemented endpoints:**

#### Health & Root Endpoints
- `GET /health` - Health check
- `GET /` - API information

#### Onboarding System 
- `GET /v1/onboarding/sections` - Retrieve form sections
- `POST /v1/onboarding/responses` - Submit form responses

#### Activity Tracking
- `GET /v1/activities/` - List activities with filtering/pagination
- `GET /v1/activities/types` - Available activity types
- `GET /v1/activities/{id}` - Specific activity details

#### Food Management
- `POST /v1/food/photo` - Food photo analysis
- `POST /v1/food/` - Create food item
- `GET /v1/food/{id}` - Retrieve food by ID
- `PUT /v1/food/{id}` - Update food information
- `POST /v1/food/{id}/macros` - Update macros by portion

#### Ingredients Management
- `POST /v1/food/{id}/ingredients/` - Add ingredient
- `GET /v1/food/{id}/ingredients/` - List ingredients
- `PUT /v1/food/{id}/ingredients/{id}` - Update ingredient
- `DELETE /v1/food/{id}/ingredients/{id}` - Delete ingredient

#### Macros & Nutrition
- `POST /v1/macros/calculate` - Calculate from onboarding
- `POST /v1/macros/consumed` - Update consumption
- `GET /v1/macros/daily` - Daily macro status

#### Food Database
- `GET /v1/food-database/` - List foods (paginated)
- `POST /v1/food-database/` - Add food to database
- `POST /v1/food-database/search` - Search foods
- `GET /v1/food-database/popular` - Popular foods

### 2. Performance Tests (`test_performance.py`)

**Performance and load testing:**

#### Response Time Testing
- Individual endpoint performance
- Response time consistency
- Performance thresholds validation

#### Concurrent Load Testing
- Multiple simultaneous requests
- Concurrent user simulation
- Resource usage patterns

#### End-to-End Performance
- Complete user workflow timing
- Performance breakdown analysis
- Scalability testing

### 3. Validation Tests (`test_validation.py`)

**Input validation and error handling:**

#### Input Validation
- Required field validation
- Data type validation
- Range and boundary testing
- File upload validation

#### Error Response Testing
- Consistent error structures
- Appropriate HTTP status codes
- Validation error details

#### Edge Cases
- Boundary value testing
- Special character handling
- Unicode support
- Large data handling

## 🎯 Test Fixtures & Data

### Shared Fixtures (conftest.py)
- **API Client**: HTTP client for testing
- **Sample Data**: Valid test data for all endpoints
- **Invalid Data**: Invalid data for validation testing
- **Helper Functions**: Response structure validation
- **Environment Setup**: Automatic server health checks

### Test Data Examples
```python
# Valid food data
{
    "name": "Test Chicken Breast",
    "brand": "Test Farm", 
    "serving_size": 100.0,
    "calories_per_serving": 165.0,
    "macros_per_serving": {
        "protein": 31.0,
        "carbs": 0.0,
        "fat": 3.6,
        "fiber": 0.0
    }
}

# Valid onboarding data
{
    "age": 28,
    "gender": "female",
    "height": 165.0,
    "weight": 60.0,
    "activity_level": "lightly_active",
    "goal": "maintain_weight"
}
```

## 🏃‍♂️ Running Tests

### Using Test Runner Script

```bash
# Quick commands
python run_tests.py health          # Health check only
python run_tests.py fast            # Fast tests (excludes slow ones)
python run_tests.py api             # All API tests
python run_tests.py performance     # Performance tests
python run_tests.py validation      # Validation tests

# With options
python run_tests.py all --html       # Generate HTML report
python run_tests.py api --verbose    # Verbose output
python run_tests.py fast --parallel  # Run in parallel

# Custom server URL
python run_tests.py api --server-url http://staging.example.com:8000
```

### Using Pytest Directly

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_api_endpoints.py
pytest tests/test_performance.py
pytest tests/test_validation.py

# Run by markers
pytest -m "api"                    # API tests only
pytest -m "performance"            # Performance tests only
pytest -m "api and not slow"       # Fast API tests

# With options
pytest -v                          # Verbose
pytest --html=report.html          # HTML report
pytest --cov=api                   # Coverage report
pytest -n auto                     # Parallel execution
```

### Test Markers

The test suite uses pytest markers for organizing tests:

- `@pytest.mark.api` - API integration tests
- `@pytest.mark.performance` - Performance tests  
- `@pytest.mark.validation` - Validation tests
- `@pytest.mark.integration` - Integration tests (slow)
- `@pytest.mark.unit` - Unit tests (fast)

## 📊 Test Reports

### HTML Reports
```bash
python run_tests.py all --html
# Opens: test_reports/report.html
```

### Coverage Reports
```bash
python run_tests.py coverage
# Terminal output + htmlcov/index.html
```

### JUnit XML (CI/CD)
```bash
python run_tests.py all --junit
# Generates: test_reports/junit.xml
```

## 🔧 Configuration

### Environment Variables
- `TEST_BASE_URL` - API server URL (default: http://localhost:8000)

### Pytest Configuration (pytest.ini)
```ini
[tool:pytest]
testpaths = tests
addopts = --verbose --tb=short --color=yes
markers =
    api: API integration tests
    performance: Performance tests
    validation: Validation tests
```

## 🎯 Test Coverage

### Current Coverage
- ✅ **100% Endpoint Coverage** - All implemented endpoints tested
- ✅ **Validation Testing** - All input validation scenarios
- ✅ **Error Handling** - All error conditions tested
- ✅ **Performance Testing** - Response times and load testing
- ✅ **Integration Testing** - End-to-end user workflows

### Test Scenarios Per Endpoint

| Endpoint | Functional | Validation | Performance | Error Cases |
|----------|------------|------------|-------------|-------------|
| Health Check | ✅ | ✅ | ✅ | ✅ |
| Onboarding | ✅ | ✅ | ✅ | ✅ |
| Activities | ✅ | ✅ | ✅ | ✅ |
| Food Management | ✅ | ✅ | ✅ | ✅ |
| Ingredients | ✅ | ✅ | ✅ | ✅ |
| Macros | ✅ | ✅ | ✅ | ✅ |
| Food Database | ✅ | ✅ | ✅ | ✅ |

## 🐛 Debugging Failed Tests

### Common Issues
1. **Server Not Running**: Ensure API server is started
2. **Wrong Port**: Check server URL matches actual port
3. **Dependencies Missing**: Install all test dependencies
4. **Database Issues**: Currently using mock data, but prepare for DB issues

### Debug Commands
```bash
# Verbose output with full tracebacks
pytest -v --tb=long

# Run single test for debugging  
pytest tests/test_api_endpoints.py::TestHealthAndRoot::test_health_check -v

# Debug with pdb
pytest --pdb tests/test_api_endpoints.py::test_specific_function
```

## 🚀 CI/CD Integration

### GitHub Actions Example
```yaml
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start API server
        run: uvicorn api.main:app --host 0.0.0.0 --port 8000 &
      - name: Wait for server
        run: sleep 10
      - name: Run tests
        run: python run_tests.py all --junit
      - name: Upload test results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_reports/
```

## 🔮 Future Enhancements

### Planned Test Additions
1. **Database Integration Tests** - When real DB is connected
2. **Authentication Tests** - When user auth is implemented  
3. **File Upload Tests** - Real image processing tests
4. **External API Tests** - ChatGPT/AI service integration
5. **Security Tests** - SQL injection, XSS prevention
6. **Load Testing** - Higher concurrent user simulation

### Test Data Management
1. **Database Seeding** - Consistent test data setup
2. **Test Isolation** - Proper cleanup between tests
3. **Mock Services** - Mock external API dependencies
4. **Test Environments** - Separate test/staging environments

## 📚 Additional Resources

- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest Documentation](https://docs.pytest.org/)
- [HTTPx Testing Guide](https://www.python-httpx.org/advanced/#testing)
- [API Testing Best Practices](https://assertible.com/blog/7-http-methods-for-testing-rest-apis)

---

**Happy Testing! 🧪✨** 