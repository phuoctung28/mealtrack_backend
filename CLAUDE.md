# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
uvicorn src.api.main:app --reload  # Development server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000  # Production server
```

### Testing
```bash
# Quick test runner with various options
python run_tests.py health      # Quick health check
python run_tests.py fast        # Fast tests only
python run_tests.py api         # API integration tests
python run_tests.py validation  # Validation tests
python run_tests.py performance # Performance tests
python run_tests.py coverage    # Tests with coverage
python run_tests.py all         # All tests

# Direct pytest usage
pytest                          # Run all tests
pytest -m "api and not slow"    # API tests excluding slow ones
pytest -m fast                  # Fast tests only
pytest -m performance          # Performance tests only
pytest tests/test_api_endpoints.py::TestHealthAndRoot  # Specific test
```

### Database
```bash
python scripts/setup_db.py     # Setup MySQL database (production)
# SQLite database is auto-created for development
```

## Architecture Overview

This is a FastAPI-based meal tracking application following Clean Architecture (4-layer pattern):

### Layer Structure
- **Presentation (`api/`)**: HTTP endpoints, routers, request/response handling
- **Application (`app/`)**: Use cases, handlers, background jobs
- **Domain (`domain/`)**: Core business logic, entities, services, ports
- **Infrastructure (`infra/`)**: External services, repositories, database adapters

### Key Components

#### Domain Layer
- **Models**: Core entities (Meal, Nutrition, Ingredient, TDEE, etc.)
- **Ports**: Abstract interfaces for external services
- **Services**: Business logic (TdeeService, NutritionService, etc.)

#### Application Layer
- **Handlers**: Process business operations (meal_handler, tdee_handler, etc.)
- **Jobs**: Background processing (analyse_meal_image_job, enrich_nutrition_job)

#### Infrastructure Layer
- **Adapters**: External service implementations (Cloudinary, Vision AI, USDA Food DB)
- **Repositories**: Data persistence (meal_repository)
- **Database**: SQLAlchemy models and configuration

### Core Features
- **AI Meal Analysis**: Upload meal images for automatic nutritional analysis using GPT-4 Vision
- **Background Processing**: Asynchronous meal analysis with status tracking
- **TDEE Calculation**: Total Daily Energy Expenditure based on user activity
- **Cloud Storage**: Cloudinary integration for image storage
- **Database Support**: SQLite (development) and MySQL (production)

### API Endpoints
- `/v1/meals/` - Meal management and photo analysis
- `/v1/macros/` - Macronutrient tracking
- `/v1/activities/` - Activity and exercise tracking
- `/v1/tdee/` - TDEE calculations
- `/health` - Health check endpoint

### Database Migration
Uses Alembic for database migrations:
- Configuration: `alembic.ini`
- Migration files: `migrations/versions/`
- Run migrations: `alembic upgrade head`

### Environment Configuration
Required environment variables:
- `OPENAI_API_KEY` - For GPT-4 Vision analysis
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` - For image storage
- `USE_SQLITE=1` - Use SQLite for development
- `USE_MOCK_STORAGE=1` - Use local storage instead of Cloudinary

### Testing Strategy
- **Markers**: `api`, `unit`, `integration`, `performance`, `validation`, `slow`, `fast`
- **Structure**: Tests organized by layer and functionality
- **Custom Runner**: `run_tests.py` provides convenient test execution options
- **Health Checks**: Server health verification before running tests