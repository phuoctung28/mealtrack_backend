---
phase: 3
title: Mobile Integration
status: completed
priority: P1
effort: 4h
dependencies:
  - 1
  - 2
---

# Phase 3: Mobile Integration

## Overview

Wire mobile to the backend snapshot while preserving the existing dashboard card surface. The app maps the API response into `GoalMomentumSnapshot` and falls back to current weight-progress behavior if the endpoint fails.

## Requirements

- Functional: dashboard ribbon progress percent comes from backend journey snapshot.
- Functional: API failure does not hide or break the card.
- Functional: meal, hydration, and movement mutations invalidate the journey snapshot.
- Non-functional: no local SharedPreferences action-progress source of truth.

## Architecture

Add Freezed API models to `progress_models.dart`, a Retrofit method to `ApiService`, a provider in `progress_providers.dart`, and update `goal_momentum_snapshot_provider.dart` to adapt backend response into the existing domain entity.

## Related Code Files

- Modify: `/Users/tonytran/Projects/nutree-universe/worktrees/mobile-journey-progress-card/lib/core/network/api_service.dart`
- Modify: `/Users/tonytran/Projects/nutree-universe/worktrees/mobile-journey-progress-card/lib/features/progress/data/models/progress_models.dart`
- Modify: `/Users/tonytran/Projects/nutree-universe/worktrees/mobile-journey-progress-card/lib/features/progress/application/providers/progress_providers.dart`
- Modify: `/Users/tonytran/Projects/nutree-universe/worktrees/mobile-journey-progress-card/lib/features/progress/application/providers/goal_momentum_snapshot_provider.dart`
- Modify: hydration/movement log providers and dashboard host invalidation paths as needed.

## Implementation Steps

1. Add `JourneyProgressResponse`, breakdown, and latest-action Freezed models.
2. Add `ApiService.getJourneyProgress()`.
3. Add provider that fetches `/progress/journey`.
4. Map backend action source strings to `GoalMomentumActionSource`.
5. Update current snapshot provider to use backend response with weight fallback.
6. Invalidate journey provider after meal save, hydration log/delete, and movement log/update/delete.
7. Regenerate Dart code.

## Success Criteria

- [ ] Existing `WaveRibbonCard` receives backend progress via `GoalMomentumSnapshot`.
- [ ] Provider test proves backend percent wins over weight percent.
- [ ] Provider test proves fallback remains weight progress if API throws.
- [ ] Generated Retrofit/Freezed files are updated.

## Risk Assessment

Risk: stale percent after logging actions. Mitigation: explicit provider invalidation at all mutation paths that can create/delete counted actions.
