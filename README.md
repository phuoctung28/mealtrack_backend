# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development with MySQL
```bash
./scripts/local.sh
./scripts/stop-local.sh
./scripts/cleanup-db.sh 
```

## Architecture Overview

This is a FastAPI-based meal tracking application following Clean Architecture (4-layer pattern):

### Layer Structure
- **Presentation (`src/api/`)**: HTTP endpoints, routers, request/response handling
- **Application (`src/app/`)**: Use cases, handlers, background jobs
- **Domain (`src/domain/`)**: Core business logic, entities, services, ports
- **Infrastructure (`src/infra/`)**: External services, repositories, database adapters

#### Event Bus Registration
All handlers must be registered in `src/api/dependencies/event_bus.py`