# MealTrack Backend

A sophisticated FastAPI-based microservice for meal tracking and nutritional analysis.

## Quick Links

- **[Project Overview & PDR](./docs/project-overview-pdr.md)** - Vision, goals, and requirements.
- **[System Architecture](./docs/system-architecture.md)** - Multi-layer architecture and data flow.
- **[Code Standards](./docs/code-standards.md)** - Development guidelines and patterns.
- **[Codebase Summary](./docs/codebase-summary.md)** - Directory structure and file organization.
- **[Project Roadmap](./docs/project-roadmap.md)** - Future plans and completed features.

## 🚀 Features

- **AI-Powered Meal Analysis**: Vision-based food recognition with 6 meal strategies, food-label image analysis, and provider fallback routing.
- **Catalog-Backed Meal Recommendations**: Deterministic three-day plans built from the curated catalog, with durable slot summaries and swap/log/skip flows.
- **API Surface**: 31 route files, 29 router registrations in `main.py`, and 98 standard `@router` verb handlers plus the two health `api_route` declarations that serve GET+HEAD.
- **CQRS Architecture**: Commands, queries, events, and handlers wired through a PyMediator singleton event bus.
- **Vector Cache**: Active meal-image-name vector cache uses `pgvector`; Pinecone is legacy documentation only and is not a runtime adapter.
- **Multi-Language Support**: 7 languages (en, vi, es, fr, de, ja, zh) with translation service.
- **Smart Notifications**: FCM push with timezone-aware scheduling and preferences.

## 🛠 Technology Stack

- **Core**: FastAPI 0.136.3 (Python 3.13.2), SQLAlchemy 2.0 async runtime (`AsyncSession`, `AsyncUnitOfWork`).
- **Database**: PostgreSQL (Neon) with SQLAlchemy 2.0, Redis 7.0 for selective optional caching; required state is modeled separately.
- **AI**: OpenAI via LangChain/Responses API as the default text and vision provider, with optional Cloudflare Workers AI routing for configured text purposes and vision fallback. Gemini packages remain in dependencies, but the runtime provider registry is OpenAI + Cloudflare.
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

1. **API Layer** (97 files, 12,709 LOC): route modules, middleware, schemas, dependencies, and API mappers.
2. **Application Layer** (244 files, 14,684 LOC): CQRS command/query/event handlers and orchestration services.
3. **Domain Layer** (192 files, 19,522 LOC): entities, services, ports, policies, and bounded contexts.
4. **Infrastructure Layer** (162 files, 17,762 LOC): database models, repositories, external adapters, cache, observability, and event bus implementation.

## 🚦 Getting Started

```bash
# Clone and enter repo
git clone <repo-url> && cd backend

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env # Configure variables

# Local development flow
./scripts/development/local.sh

# Or run the app directly after the database is ready
uvicorn src.api.main:app --reload
```

Production uses `python migrations/run.py` as the pre-deploy command. The
production container then starts through `docker-entrypoint.sh` without
re-running migrations; non-production containers run migrations at startup.

- **Swagger Docs**: http://localhost:8000/docs
- **Tests**: `pytest tests/unit --cov=src --cov-fail-under=65` for the default CI-aligned suite. Broad unscoped `pytest` currently hits two duplicate-package import collisions, so prefer targeted paths.
