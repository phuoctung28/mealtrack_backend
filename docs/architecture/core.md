# Core Architecture

**Version:** 0.4.7
**Last Updated:** January 11, 2026

## System Overview

MealTrack Backend follows a **4-Layer Clean Architecture** combined with **CQRS** (Command Query Responsibility Segregation) and **Event-Driven Design**.

### Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                     Client Applications                         │
│          (Mobile Apps, Web Apps, Third-party clients)           │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTPS/REST/WebSocket
                         ▼
        ┌────────────────────────────────────────┐
        │   FastAPI Application (src/api)        │
        │  - HTTP Routing, Request Handling      │
        │  - Response Serialization              │
        └────────┬─────────────────────────────┘
                 │ Commands/Queries
                 ▼
    ┌────────────────────────────────────────────────┐
    │  Application Layer (src/app) - CQRS            │
    │  - CommandBus/QueryBus Dispatch                │
    │  - Event Publishing                            │
    └────────┬──────────────────────────────────────┘
             │ Domain Services & Ports
             ▼
  ┌──────────────────────────────────────────────────┐
  │   Domain Layer (src/domain) - Business Logic     │
  │  - Entities & Value Objects                      │
  │  - Domain Services                               │
  └────────┬───────────────────────────────────────┘
           │ Repositories & Adapters
           ▼
      ┌────────────────────────────────────────┐
      │   Infrastructure Layer (src/infra)    │
      │  - Repositories                        │
      │  - Database (MySQL)                    │
      │  - External Services                   │
      └────────────────────────────────────────┘
```

## Layers

### 1. API Layer (Presentation)
- **Location**: `src/api/`
- **Responsibility**: Handle HTTP requests, validate inputs via Pydantic, serialize responses.
- **Key Patterns**: Dependency injection via `FastAPI.Depends()`.

### 2. Application Layer
- **Location**: `src/app/`
- **Responsibility**: Orchestrate commands/queries, coordinate domain services.
- **Pattern**: CQRS with separated Read (Queries) and Write (Commands) paths.

### 3. Domain Layer
- **Location**: `src/domain/`
- **Responsibility**: Core business logic, entities, and validation.
- **Independence**: Zero framework dependencies.

### 4. Infrastructure Layer
- **Location**: `src/infra/`
- **Responsibility**: Data persistence (SQLAlchemy), external integrations (AI, Auth), and technical concerns (Caching, Event Bus).
