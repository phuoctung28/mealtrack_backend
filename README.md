# MealTrack Backend

A sophisticated FastAPI-based microservice for meal tracking and nutritional analysis with AI vision capabilities, intelligent meal planning, and personalized nutrition insights.

## Quick Links

- **[Project Overview & PDR](./docs/project-overview-pdr.md)** - Vision, goals, requirements, success metrics
- **[System Architecture](./docs/system-architecture.md)** - Architecture patterns, data flow, integrations
- **[Codebase Summary](./docs/codebase-summary.md)** - Project structure, modules, dependencies
- **[Code Standards](./docs/code-standards.md)** - Style guide, patterns, conventions
- **[API Documentation](./docs/api-docs.md)** - Endpoint details (auto-generated via Swagger)

## Features

- **AI-Powered Meal Analysis**: Google Gemini 2.0 vision for food recognition and nutritional extraction
- **Ingredient Recognition**: AI-powered ingredient identification from meal images
- **Intelligent Meal Planning**: AI-generated personalized meal plans with dietary preferences and ingredient-based meal suggestions
- **Meal Suggestions**: Generate and save AI-driven meal recommendations based on user preferences
- **Real-time Chat**: WebSocket-based nutrition advice with AI conversation and context awareness
- **Meal Tracking & History**: Complete meal logging with manual entry and image-based analysis
- **Nutritional Insights**: Daily summaries, macro tracking, TDEE calculations
- **Push Notifications**: Firebase Cloud Messaging with timezone-aware scheduling
- **User Pain Points**: Capture and track user health concerns during onboarding
- **Vector Search**: Pinecone-powered semantic food discovery
- **Feature Management**: Dynamic feature flags for gradual rollouts
- **Clean Architecture**: 4-layer architecture with CQRS pattern and event-driven design

## Technology Stack

**Core**:
- FastAPI 0.115.0+ (async web framework)
- Python 3.8+ (async/await support)
- SQLAlchemy 2.0 (ORM)
- Pydantic v2 (validation)

**Data**:
- MySQL 8.0+ (primary database)
- Redis 7.0+ (caching)
- Alembic (migrations)

**AI/ML**:
- Google Gemini 2.0 (vision API)
- OpenAI GPT-4 (chat/planning)
- Pinecone (vector embeddings)
- LangChain (LLM orchestration)

**Integration**:
- Firebase Admin SDK (auth, messaging)
- USDA FoodData Central (nutrition database)
- Cloudinary (image storage)

**Quality**:
- pytest (testing framework)
- ruff (linting), black (formatting), mypy (type checking)
- 70%+ code coverage

## Architecture Overview

The application follows a **4-Layer Clean Architecture** with **CQRS** pattern:

```
API Layer (HTTP Routes)
    ↓
Application Layer (Commands/Queries)
    ↓
Domain Layer (Business Logic)
    ↓
Infrastructure Layer (Databases, APIs)
```

**Key Patterns**:
- Event-Driven Architecture for loose coupling
- Dependency Injection for testability
- Repository Pattern for data access
- Strategy Pattern for pluggable algorithms
- Async-first for performance

See [System Architecture](./docs/system-architecture.md) for detailed diagrams and patterns.

## Getting Started

### Prerequisites
- Python 3.8+
- MySQL 8.0+
- Redis 7.0+
- Docker (optional)

### Development Setup

```bash
# Clone repository
git clone <repo-url>
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Run migrations
python -m alembic upgrade head

# Start development server
uvicorn src.api.main:app --reload
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Overview

### Core Endpoints (70+ total)

**Meals**:
- `POST /v1/meals/image/analyze` - Analyze meal image with AI vision
- `POST /v1/meals/manual` - Log meal manually
- `GET /v1/meals/{id}` - Get meal details
- `PATCH /v1/meals/{id}` - Edit meal details

**Ingredients & Suggestions**:
- `POST /v1/ingredients/recognize` - AI-powered ingredient recognition from image
- `POST /v1/meal-suggestions/generate` - Generate AI meal suggestions
- `POST /v1/meal-suggestions/{id}/save` - Save suggestion as meal

**Meal Planning**:
- `POST /v1/meal-plans/generate` - Generate AI meal plan
- `POST /v1/meal-plans/generate/weekly-ingredient-based` - Generate plan with ingredient options
- `GET /v1/meal-plans/{id}` - Get meal plan
- `PUT /v1/meal-plans/{id}/meals/{day}` - Replace meal in plan
- `GET /v1/meals/by-date` - Get meals by date range

**Chat**:
- `POST /v1/chat/threads` - Create chat thread
- `POST /v1/chat/threads/{id}/messages` - Send message
- `GET /v1/chat/threads/{id}/messages` - Get message history
- `WebSocket /v1/chat/ws/{thread_id}` - Real-time chat stream

**Users**:
- `POST /v1/users/sync` - Sync user from Firebase
- `POST /v1/users/onboarding` - Complete user onboarding with pain points
- `GET /v1/user-profiles/me` - Get user profile
- `PUT /v1/user-profiles/me` - Update profile with timezone

**Notifications**:
- `POST /v1/notifications/tokens` - Register FCM token
- `PUT /v1/notifications/preferences` - Update notification preferences

**Other**:
- `GET /v1/foods/search` - Search USDA food database
- `GET /v1/feature-flags/{flag}` - Check feature flag status
- `POST /v1/webhooks/revenucat` - RevenueCat subscription webhooks

See [Project Overview](./docs/project-overview-pdr.md#api-surface-area) for complete endpoint listing.

## Configuration

See `.env.example` for all available environment variables. Key variables:

**Essential**:
- `ENVIRONMENT`: development/production/staging
- MySQL: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Redis: `REDIS_URL`
- Firebase: `FIREBASE_CREDENTIALS` or `FIREBASE_SERVICE_ACCOUNT_JSON`

**AI Services**:
- `GOOGLE_API_KEY`: Gemini vision API
- `OPENAI_API_KEY`: GPT-4 chat/planning
- `USDA_FDC_API_KEY`: Food database
- `PINECONE_API_KEY`: Vector embeddings

**Cloud Storage**:
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

See [Project Overview](./docs/project-overview-pdr.md) for complete configuration details.

## Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src

# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration
```

Target coverage: 70%+ (higher for critical paths)

See [Testing Setup](./docs/TESTING_SETUP.md) for detailed testing information.

## Development

```bash
# Code quality checks
ruff format src/           # Format code
ruff check src/            # Lint
mypy src/                  # Type checking

# All checks
ruff format src/ && isort src/ && ruff check src/ && mypy src/ && pytest

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"
```

See [Code Standards](./docs/code-standards.md) for detailed development guidelines.

## Documentation

- **[Project Overview & PDR](./docs/project-overview-pdr.md)** - Requirements and architecture
- **[System Architecture](./docs/system-architecture.md)** - Design patterns and data flow
- **[Code Standards](./docs/code-standards.md)** - Style guide and conventions
- **[Codebase Summary](./docs/codebase-summary.md)** - Module organization
- **[Testing Setup](./docs/TESTING_SETUP.md)** - Test configuration
- **Event-Driven Architecture** - See [./docs/EVENT_DRIVEN_ARCHITECTURE.md](./docs/EVENT_DRIVEN_ARCHITECTURE.md)

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and add tests
3. Run tests and code quality checks (see Development section)
4. Submit PR with description

All PRs must:
- Pass tests (100% for new code)
- Include type hints (mypy strict)
- Meet code coverage (70%+ minimum)
- Follow code standards

## License

See LICENSE file for details.