---
title: Journey Progress Card
description: >-
  Server-derived action-progress snapshot for the dashboard goal journey card
  with strict active-period boundaries.
status: pending
priority: P2
branch: feat/journey-progress-card
tags:
  - progress
  - backend
  - mobile
  - dashboard
blockedBy: []
blocks: []
created: '2026-06-21T16:41:14.580Z'
createdBy: 'ck:plan'
source: skill
---

# Journey Progress Card

## Overview

Build a canonical backend journey-progress snapshot and wire the mobile dashboard progress card to it. The backend owns period selection and strict action filtering so new users and existing users follow the same rule: only actions in the current active period count.

Brainstorm source: `plans/reports/260621-2340-journey-progress-card-brainstorm.md`

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Backend Contract](./phase-01-backend-contract.md) | Completed |
| 2 | [Backend Calculation](./phase-02-backend-calculation.md) | Completed |
| 3 | [Mobile Integration](./phase-03-mobile-integration.md) | Completed |
| 4 | [Verification and PR](./phase-04-verification-and-pr.md) | Pending |

## Dependencies

- Backend worktree: `/Users/tonytran/Projects/nutree-universe/worktrees/backend-journey-progress-card`
- Mobile worktree: `/Users/tonytran/Projects/nutree-universe/worktrees/mobile-journey-progress-card`
- Relevant completed plan: `plans/260618-0108-workout-calorie-credit-weekly-budget/plan.md`
- Unrelated pending plan: `plans/260612-1046-service-initiated-bandwidth-reduction/plan.md`
