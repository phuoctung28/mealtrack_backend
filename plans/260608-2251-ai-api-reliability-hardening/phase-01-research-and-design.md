---
phase: 1
title: Research and design
status: completed
priority: P1
effort: 1h
dependencies: []
---

# Phase 1: Research and design

## Overview

Lock the AI API failure modes and implementation boundaries before code changes.

## Requirements

- Functional: identify exact AI route/provider touchpoints and preserve stable success contracts.
- Non-functional: keep solution small, testable, and compatible with existing Clean Architecture/CQRS patterns.

## Architecture

Route handlers should keep delegating through commands/queries. Domain/infra services should preserve typed AI exceptions instead of collapsing them into generic runtime errors. Cache metadata should live at the AI infrastructure boundary, not in API code.

## Related Code Files

- Read: `src/api/routes/v1/meals.py`
- Read: `src/api/routes/v1/ingredients.py`
- Read: `src/api/routes/v1/meal_suggestions.py`
- Read: `src/infra/services/ai/ai_model_manager.py`
- Read: `src/infra/services/ai/gemini_cache_manager.py`
- Read: `src/infra/services/ai/providers/gemini_provider.py`
- Read: `src/infra/adapters/vision_ai_service.py`

## Implementation Steps

1. Confirm route-level AI endpoints and dormant handler registrations.
2. Confirm provider fallback/cache call chain.
3. Confirm existing tests and gaps for cache fallback, image outage mapping, base64 validation, and route setup.
4. Record red-team risks in `plan.md`.

## Success Criteria

- [ ] Every code touchpoint for implementation is listed.
- [ ] Scope explicitly excludes new providers, migrations, and product UX redesign.
- [ ] Red-team risks have mitigation notes.

## Risk Assessment

Main risk is confusing "AI outage" with "bad user image." Keep the distinction explicit in exceptions and tests.
