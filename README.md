# MealTrack Backend

A sophisticated FastAPI-based microservice for meal tracking and nutritional analysis.

## Quick Links

- **[Project Overview & PDR](./docs/project-overview-pdr.md)** - Vision, goals, and requirements.
- **[System Architecture](./docs/system-architecture.md)** - Multi-layer architecture and data flow.
- **[Code Standards](./docs/code-standards.md)** - Development guidelines and patterns.
- **[Codebase Summary](./docs/codebase-summary.md)** - Directory structure and file organization.
- **[Project Roadmap](./docs/project-roadmap.md)** - Future plans and completed features.

## 🚀 Features

- **AI-Powered Meal Analysis**: Vision-based food recognition with 6 analysis strategies and provider fallback routing.
- **26 Endpoint Route Modules**: 85 endpoint decorators covering meals, users, profiles, chat, notifications, meal plans, suggestions, activities, ingredients, webhooks, and support routes.
- **CQRS Architecture**: Commands, queries, events, and handlers wired through a PyMediator singleton event bus.
- **Intelligent Planning**: AI-generated weekly plans with dietary preferences, cooking time constraints, and ingredient-based generation.
- **Vector Search**: Pinecone semantic search with 1024-dim embeddings (llama-text-embed-v2).
- **Real-time Chat**: WebSocket + REST endpoints with streaming AI responses via MessageOrchestrationService.
- **Multi-Language Support**: 7 languages (en, vi, es, fr, de, ja, zh) with translation service.
- **Smart Notifications**: FCM push with timezone-aware scheduling and preferences.

## 🛠 Technology Stack

- **Core**: FastAPI 0.136.3 (Python 3.13.2), SQLAlchemy 2.0 async runtime (`AsyncSession`, `AsyncUnitOfWork`).
- **Database**: PostgreSQL (Neon) with SQLAlchemy 2.0, Redis 7.0 for selective optional caching; required state documented separately.
- **AI**: OpenAI via LangChain/Responses API as the default text and vision provider, with optional Cloudflare Workers AI routing for configured text purposes and vision fallback; Pinecone Inference API for embeddings.
- **Infrastructure**: Firebase (JWT Auth + FCM), Cloudinary (image storage), RevenueCat (subscriptions).
- **Event Bus**: PyMediator with singleton registry for CQRS.
- **Testing**: pytest (unit-biased default config), ruff (linting), mypy (type checking).

### OpenAI Prompt Caching

- OpenAI calls run through LangChain `ChatOpenAI` with Responses API enabled.
- Enable provider-side prompt caching with `OPENAI_PROMPT_CACHE_ENABLED`.
- Optional retention uses `OPENAI_PROMPT_CACHE_RETENTION`; key namespace uses `OPENAI_PROMPT_CACHE_KEY_PREFIX`.
- Cache keys are derived from the model, purpose, and a hash of the system prompt. They never include raw user prompt text, images, emails, or IDs.
- Track `ai.openai.prompt_cache.request.count`, `ai.openai.prompt_cache.cached_tokens`, and `ai.openai.prompt_cache.input_tokens` before assuming savings.

## 🏗 Architecture

Follows a **4-Layer Clean Architecture** with **CQRS** and **Event-Driven Design**:

1. **API Layer** (91 files, 10,624 LOC): 26 endpoint route modules, 85 endpoint decorators, schemas, middleware, dependencies, and API mappers.
2. **Application Layer** (207 files, 11,192 LOC): CQRS command/query/event handlers and orchestration services.
3. **Domain Layer** (166 files, 16,283 LOC): entities, services, ports, policies, and bounded contexts.
4. **Infrastructure Layer** (154 files, 15,134 LOC): database models, repositories, external adapters, cache, observability, and event bus implementation.

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
- **Tests**: `pytest` for the default non-integration suite; CI runs `pytest tests/unit --cov=src --cov-fail-under=65`
