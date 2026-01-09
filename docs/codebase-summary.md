# MealTrack Backend - Codebase Summary

**Generated:** January 9, 2026
**Codebase Stats**: 547 files, 752k+ tokens, 3.5M+ characters
**Source Files**: ~320+ Python files (src/)
**Test Files**: 76 files with 681+ test cases
**Language**: Python 3.11+
**Framework**: FastAPI 0.115.0+, SQLAlchemy 2.0
**Architecture**: 4-Layer Clean Architecture + CQRS + Event-Driven
**Status**: Phase 02 Complete (Language Prompt Integration). Phase 06 Session-Based Suggestions Active.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Directory Layout](#directory-layout)
3. [Layer Responsibilities](#layer-responsibilities)
4. [Key Files & Modules](#key-files--modules)
5. [Module Dependencies](#module-dependencies)
6. [Entry Points](#entry-points)
7. [Data Models](#data-models)
8. [API Routes](#api-routes)
9. [Core Services](#core-services)
10. [Testing Organization](#testing-organization)

---

## Project Structure

### High-Level Architecture

```
mealtrack_backend/
├── src/                                 # Application source code (322 files)
│   ├── api/                             # API Layer (HTTP endpoints)
│   │   ├── routes/v1/                   # 15+ endpoint files (70+ routes)
│   │   ├── schemas/                     # 35+ Pydantic models
│   │   ├── mappers/                     # Domain to API conversion
│   │   ├── dependencies/                # FastAPI DI providers
│   │   ├── middleware/                  # HTTP middleware
│   │   └── utils/                       # API utilities
│   ├── app/                             # Application Layer (CQRS)
│   │   ├── commands/                    # 40+ command definitions
│   │   ├── queries/                     # 35+ query definitions
│   │   ├── events/                      # 20+ domain events
│   │   └── handlers/                    # 60+ total handlers
│   ├── domain/                          # Domain Layer (Business logic)
│   │   ├── model/                       # 30+ domain entities
│   │   ├── services/                    # 40+ service files
│   │   ├── strategies/                  # Strategy implementations
│   │   ├── ports/                       # Interface definitions
│   │   └── prompts/                     # AI prompt templates
│   └── infra/                           # Infrastructure Layer
│       ├── database/                    # SQLAlchemy + Alembic (12 migrations)
│       ├── repositories/                # 10+ data access implementations
│       ├── services/                    # External service adapters
│       ├── cache/                       # Redis caching
│       ├── event_bus/                   # Event dispatcher
│       └── adapters/                    # Storage & integrations
├── tests/                               # Test suite (76 files, 681+ tests)
├── migrations/                          # Database migrations (12 versions)
├── docs/                                # Documentation
├── scripts/                             # Utility scripts
├── requirements.txt                     # Python dependencies
└── .env.example                         # Environment template
```

### Codebase Metrics (Updated Jan 2026)

| Metric | Value |
|--------|-------|
| Total Files | 398 source files |
| Source Files (src/) | ~322 files |
| Test Files | 76 files |
| Total Test Cases | 681+ tests |
| Total Tokens | 267,486 |
| Total Characters | 1.2M+ |
| Lines of Code (src/) | ~34,132 LOC |
| API Endpoints | 70+ REST endpoints |
| CQRS Commands | 40+ command definitions |
| CQRS Queries | 35+ query definitions |
| Database Tables | 27 tables across 12 migrations |
| Code Coverage | 70%+ maintained |

---

## Directory Layout

### Complete Directory Tree

```
src/
├── api/                                 # Presentation Layer (~8,330 LOC)
│   ├── main.py                          # FastAPI app initialization
│   ├── routes/v1/                       # 15+ route files
│   │   ├── meals.py                     # 6 endpoints
│   │   ├── meal_suggestions.py          # 7 endpoints (Phase 06)
│   │   ├── chat/                        # Chat endpoints
│   ├── schemas/                         # Pydantic models
│   ├── mappers/                         # Entity -> Schema converters
│
├── app/                                 # Application Layer (~6,359 LOC - CQRS)
│   ├── commands/                        # 40+ command definitions
│   ├── queries/                         # 35+ query definitions
│   ├── events/                          # Domain event definitions
│   └── handlers/                        # 60+ total implementations
│
├── domain/                              # Domain Layer (~11,765 LOC)
│   ├── model/                           # 30+ domain entities
│   ├── services/                        # 40+ service files
│   ├── strategies/                      # Strategy implementations
│   ├── ports/                           # Interface definitions
│   └── prompts/                         # AI prompt templates
│
└── infra/                               # Infrastructure Layer (~7,678 LOC)
    ├── database/                        # SQLAlchemy + Alembic (12 migrations)
    ├── repositories/                    # 10+ data access implementations
    ├── services/                        # External service adapters (Pinecone 1024-dim)
    ├── cache/                           # Redis caching
    └── event_bus/                       # Event dispatcher
```

---

## Layer Responsibilities

### 1. API Layer (`src/api/`)
**Purpose**: Handle HTTP requests/responses.
**Responsibilities**: Validate requests, call commands/queries, serialize responses, handle auth.

### 2. Application Layer (`src/app/`)
**Purpose**: Implement CQRS pattern for decoupled operations.
**Responsibilities**: Command/Query handlers, publish domain events, coordinate transactions.

### 3. Domain Layer (`src/domain/`)
**Purpose**: Encapsulate core business logic.
**Responsibilities**: Domain models, business rules, validation, port interfaces.

### 4. Infrastructure Layer (`src/infra/`)
**Purpose**: Implement technical concerns and integrations.
**Responsibilities**: Persistence, external API adapters (Gemini, OpenAI, Pinecone), caching, event bus.

---

## Key Files & Modules

| File | Purpose |
|------|---------|
| `src/api/main.py` | FastAPI app initialization |
| `src/infra/database/config.py` | Database connection setup |
| `src/infra/services/ai/gemini_service.py` | Meal image analysis |
| `src/infra/services/pinecone_service.py` | Vector search (1024-dim vectors) |
| `src/domain/services/meal_service.py` | Meal business logic |
| `src/infra/event_bus/event_bus.py` | CQRS event dispatcher |

---

## Core Services

**PineconeNutritionService (Phase 05 - 1024-dim vectors)**:
Integrates Pinecone's Inference API with `llama-text-embed-v2` for 1024-dimension embeddings.

**Meal Service**:
Manages meal lifecycle from PROCESSING to READY via state machine.

**Suggestion Orchestration Service (Phase 06, Phase 01 Multilingual)**:
Handles session-based suggestions with 4h TTL in Redis. Supports 7 languages (en, vi, es, fr, de, ja, zh) via ISO 639-1 language codes with English fallback for invalid codes.

---

## Testing Organization
- **Total Tests**: 681+ passing
- **Coverage**: 70%+ overall
- **Organization**: `tests/unit/` (Domain/App logic) and `tests/integration/` (API/Infra)
- **Phase 05 Updates**: Pinecone Inference API mocks updated for 1024-dim vectors.
