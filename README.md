# MealTrack Backend

A sophisticated FastAPI-based microservice for meal tracking and nutritional analysis.

## Quick Links

- **[Project Overview & PDR](./docs/project-overview-pdr.md)** - Vision, goals, and requirements.
- **[System Architecture](./docs/architecture/index.md)** - Multi-layer architecture and data flow.
- **[Code Standards](./docs/standards/index.md)** - Development guidelines and patterns.
- **[Codebase Summary](./docs/codebase-summary.md)** - Directory structure and file organization.
- **[Project Roadmap](./docs/project-roadmap.md)** - Future plans and completed features.

## 🚀 Features

- **AI-Powered Meal Analysis**: Vision-based food recognition via Gemini 2.5 Flash.
- **Session-Based Suggestions**: Personalized real-time recommendations (Phase 06).
- **Intelligent Planning**: AI-generated weekly and ingredient-based meal plans.
- **Vector Search**: Semantic food discovery using 1024-dim vectors (Phase 05).
- **Real-time Chat**: WebSocket-based nutrition advice via GPT-4.
- **Notifications**: Timezone-aware FCM push notifications.

## 🛠 Technology Stack

- **Core**: FastAPI (Python 3.11+), SQLAlchemy 2.0 (Async).
- **Data**: MySQL 8.0, Redis 7.0 (Caching/Sessions).
- **AI**: Google Gemini 2.5 Flash, OpenAI GPT-4, Pinecone (llama-text-embed-v2).
- **Infra**: Firebase (Auth/FCM), Cloudinary (Images), RevenueCat (Subs).
- **QA**: pytest (681+ tests), ruff (Lint), mypy (Types).

## 🏗 Architecture

Follows a **4-Layer Clean Architecture** with **CQRS** and **Event-Driven Design**:
1. **API Layer**: HTTP Routing & Pydantic Validation.
2. **Application Layer**: Command/Query Handlers & Event Dispatching.
3. **Domain Layer**: Core Business Logic & Entities.
4. **Infrastructure Layer**: Persistence, AI Adapters & External Services.

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
