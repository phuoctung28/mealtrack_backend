# MealTrack Backend

A sophisticated FastAPI-based microservice for meal tracking and nutritional analysis.

## Quick Links

- **[Project Overview & PDR](./docs/project-overview-pdr.md)** - Vision, goals, and requirements.
- **[System Architecture](./docs/architecture/index.md)** - Multi-layer architecture and data flow.
- **[Code Standards](./docs/standards/index.md)** - Development guidelines and patterns.
- **[Codebase Summary](./docs/codebase-summary.md)** - Directory structure and file organization.
- **[Project Roadmap](./docs/project-roadmap.md)** - Future plans and completed features.

## 🚀 Features

- **AI-Powered Meal Analysis**: Vision-based food recognition with 6 analysis strategies (basic, portion-aware, ingredient-aware, weight-aware, user-context-aware, combined).
- **Broad REST Surface**: 27 router registrations and 85 route decorators covering meals, users, profiles, notifications, meal plans, suggestions, activities, ingredients, hydration, movement, and webhooks.
- **CQRS Architecture**: 50 command files, 52 query files, 14 event files, and 86 handler files with PyMediator event bus wiring.
- **Intelligent Planning**: AI-generated weekly plans with dietary preferences, cooking time constraints, and ingredient-based generation.
- **Vector Search**: PostgreSQL/pgvector-backed semantic search with 1024-dim embeddings.
- **Multi-Language Support**: 7 languages (en, vi, es, fr, de, ja, zh) with translation service.
- **Smart Notifications**: FCM push with timezone-aware scheduling and preferences.

## 🛠 Technology Stack

- **Core**: FastAPI 0.136.3 (Python 3.13.2), SQLAlchemy 2.0 async runtime (`AsyncSession`, `AsyncUnitOfWork`).
- **Database**: PostgreSQL (Neon) with pgvector and SQLAlchemy 2.0; Redis remains optional for cache-aside and AI-context caching.
- **AI**: OpenAI primary with Cloudflare Workers AI fallback for text and vision tasks; OpenAI prompt caching is enabled where configured.
- **Infrastructure**: Firebase (JWT Auth + FCM), Cloudinary (image storage), RevenueCat (subscriptions).
- **Event Bus**: PyMediator with singleton registry for CQRS.
- **Testing**: pytest suite, ruff (linting), mypy (type checking).

### OpenAI Prompt Caching

- OpenAI calls run through LangChain `ChatOpenAI` with Responses API enabled.
- Enable provider-side prompt caching with `OPENAI_PROMPT_CACHE_ENABLED`.
- Optional retention uses `OPENAI_PROMPT_CACHE_RETENTION`; key namespace uses `OPENAI_PROMPT_CACHE_KEY_PREFIX`.
- Cache keys are derived from the model, purpose, and a hash of the system prompt. They never include raw user prompt text, images, emails, or IDs.
- Track `ai.openai.prompt_cache.request.count`, `ai.openai.prompt_cache.cached_tokens`, and `ai.openai.prompt_cache.input_tokens` before assuming savings.

## 🏗 Architecture

Follows a **4-Layer Clean Architecture** with **CQRS** and **Event-Driven Design**:

1. **API Layer** (91 files, ~10.6K LOC): HTTP routing, Pydantic validation, middleware, and API mappers.
2. **Application Layer** (207 files, ~11.0K LOC): CQRS commands, queries, handlers, and orchestration services.
3. **Domain Layer** (165 files, ~16.2K LOC): Domain services, entities, policies, and port interfaces.
4. **Infrastructure Layer** (154 files, ~15.1K LOC): Database models, repositories, adapters, observability, cache, and event bus wiring.

## 🚦 Getting Started

```bash
# Clone and enter repo
git clone <repo-url> && cd backend

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env # Configure variables

# Run migrations and start server
python -m alembic upgrade head
uvicorn src.api.main:app --reload
```

- **Swagger Docs**: http://localhost:8000/docs
- **Tests**: `pytest --cov=src`
