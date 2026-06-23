---
phase: 1
title: Backend Contract
status: completed
priority: P1
effort: 2h
dependencies: []
---

# Phase 1: Backend Contract

## Overview

Add the API contract for `GET /v1/progress/journey`, register the route, and expose typed response schemas. Keep the contract small and dashboard-focused.

## Requirements

- Functional: authenticated users can fetch the active journey progress snapshot.
- Functional: response includes period bounds, percent fields, score breakdown, and optional latest action.
- Non-functional: no schema migration and no mobile visual redesign in this phase.

## Architecture

FastAPI route sends a CQRS query through the configured event bus. The response model lives in progress schemas and maps directly to the existing mobile `GoalMomentumSnapshot` shape.

## Related Code Files

- Create: `src/api/routes/v1/progress.py`
- Create: `src/app/queries/progress/get_journey_progress_query.py`
- Modify: `src/app/queries/progress/__init__.py`
- Modify: `src/api/schemas/progress_schemas.py`
- Modify: `src/api/main.py`
- Modify: `src/api/dependencies/event_bus.py`

## Implementation Steps

1. Add `JourneyProgressResponse`, `JourneyProgressBreakdown`, and `JourneyProgressAction` schemas.
2. Add `GetJourneyProgressQuery(user_id, header_timezone)`.
3. Add `/v1/progress/journey` route using auth and `X-Timezone`.
4. Register the route in `src/api/main.py`.
5. Register the query handler placeholder after Phase 2 adds it.

## Success Criteria

- [ ] Endpoint contract compiles.
- [ ] Response field names are snake_case for backend and generate clean mobile JSON keys.
- [ ] Route requires authenticated user id.

## Risk Assessment

Risk: response contract grows into analytics payload. Mitigation: only include fields the current card consumes.
