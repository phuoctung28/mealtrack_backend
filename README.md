# MealTrack Backend

FastAPI backend for meal tracking, nutrition analysis, weekly targets, hydration, movement, and subscription-backed premium features.

## Quick Links

- [Project Overview & PDR](./docs/project-overview-pdr.md)
- [System Architecture](./docs/system-architecture.md)
- [Code Standards](./docs/code-standards.md)
- [Codebase Summary](./docs/codebase-summary.md)
- [Project Roadmap](./docs/project-roadmap.md)

## Highlights

- AI meal analysis with image upload, signed upload tokens, and scan-by-URL analysis.
- Live API surface: 26 router registrations and 79 endpoint decorators across meals, users, profiles, suggestions, hydration, movement, nutrition, referrals, promo codes, health, monitoring, webhooks, and support routes.
- CQRS with PyMediator singleton event buses and async SQLAlchemy UoW boundaries.
- PostgreSQL/Neon async runtime with pgvector-enabled local compose and Redis-backed optional cache-aside paths.
- Multi-provider integrations for Firebase, Gemini, Cloudinary, RevenueCat, PostHog, Sentry, DeepL, FatSecret, OpenFoodFacts, Brave Search, Resend, and image generators.
- 1,600+ collected tests across the repo.

## Technology

- FastAPI 0.115+ on Python 3.11+
- SQLAlchemy 2.0 async runtime with asyncpg
- PostgreSQL (Neon) as the primary database
- Redis 7 for optional caching and AI-cost optimization
- Alembic migrations
- PyMediator event bus

## Architecture

The backend follows 4-layer Clean Architecture with CQRS:

1. API layer: routing, validation, middleware, dependency injection.
2. Application layer: commands, queries, handlers, and background event handlers.
3. Domain layer: business logic, entities, services, ports, and policies.
4. Infrastructure layer: database, cache, adapters, external services, and observability.

## Getting Started

```bash
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn src.api.main:app --reload
```

- Swagger docs: `http://localhost:8000/docs`
- Tests: `pytest`
