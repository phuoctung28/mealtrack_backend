---
title: "Meal catalog browser backend"
date: "2026-08-16"
status: complete
---

# Meal Catalog Browser Backend

## Context

Implemented the backend handoff for the authenticated Recipes catalog browser
from `plans/260816-2251-meal-catalog-browser-backend-handoff/plan.md`.

## What happened

- Added authenticated list/detail routes using the shared immutable catalog
  snapshot and the existing recommendation nutrition serializer.
- Added deterministic curated `popularity_rank` ordering with a fail-closed
  503 until ranks are seeded.
- Added personalized ranking from the read-only weekly-budget target,
  owner-scoped 90-day ingredient affinity, calorie allocation, and bounded
  diversity; cold starts report curated fallback metadata.
- Fixed snapshot last-good recovery for revision lookup failures and added
  rank-only exact-key reimport updates.

## Decisions

- Browse requests do not create or update weekly budgets, recommendation plans,
  candidate rows, or meal logs.
- `allergy_evaluated` remains false until canonical allergen evaluation exists.
- Home’s three-day recommendation flow remains separate.

## Validation and next steps

The venv unit suite passed 2,436 tests with 79.06% coverage; focused catalog,
snapshot, importer, target, and migration tests passed 56 cases. Staging
deployment/authenticated requests, warm/cold p95, image coverage, and curated
rank population remain release gates.
