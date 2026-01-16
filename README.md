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
- **14 REST Route Modules**: 80+ endpoints covering meals, users, profiles, chat, notifications, meal plans, suggestions, activities, ingredients, webhooks.
- **CQRS Architecture**: 21 commands, 20 queries, 11+ domain events with PyMediator event bus.
- **Intelligent Planning**: AI-generated weekly plans with dietary preferences, cooking time constraints, and ingredient-based generation.
- **Vector Search**: Pinecone semantic search with 1024-dim embeddings (llama-text-embed-v2).
- **Real-time Chat**: WebSocket + REST endpoints with streaming AI responses.
- **Multi-Language Support**: 7 languages (en, vi, es, fr, de, ja, zh) with translation service.
- **Smart Notifications**: FCM push with timezone-aware scheduling and preferences.

## 🛠 Technology Stack

- **Core**: FastAPI 0.115+ (Python 3.11+), SQLAlchemy 2.0 with request-scoped sessions.
- **Database**: MySQL 8.0 (11 core tables), Redis 7.0 (caching with graceful degradation).
- **AI**: Google Gemini 2.5 Flash (multi-model for rate distribution), Pinecone Inference API (1024-dim).
- **Infrastructure**: Firebase (JWT Auth + FCM), Cloudinary (image storage), RevenueCat (subscriptions).
- **Event Bus**: PyMediator with singleton registry for CQRS.
- **Testing**: pytest (681+ tests, 70%+ coverage), ruff (linting), mypy (type checking).

## 🏗 Architecture

Follows a **4-Layer Clean Architecture** with **CQRS** and **Event-Driven Design**:

1. **API Layer** (74 files, ~8,244 LOC): HTTP routing, Pydantic validation, 8 mappers, 3-layer middleware.
2. **Application Layer** (136 files, ~5,967 LOC): CQRS - 21 commands, 20 queries, 11+ events, 49 handlers.
3. **Domain Layer** (124 files, ~14,236 LOC): 50 domain services, 8 bounded contexts, 15 port interfaces, 6 analysis strategies.
4. **Infrastructure Layer** (74 files, ~8,505 LOC): 11 database models, 10+ repositories, external service adapters, Redis cache, PyMediator event bus.

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
