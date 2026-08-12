---
phase: 1
title: "Contract and cleanup"
status: complete
effort: ""
---

# Phase 1: Contract and cleanup

## Overview

Make the authenticated claim contract explicit and identify stale anonymous and
passwordless paths before implementation.

## Implementation Steps

1. Keep the web lead/correlation and RevenueCat Redemption Link contract.
2. Remove passwordless/email-link and anonymous activation from the active claim UX.
3. Preserve optional Google/Apple account linking for normal account recovery.
4. Define deterministic claim errors and retry semantics.

## Success Criteria

- [x] One documented authenticated flow is used by all three repositories.
- [x] No active UI directs buyers to Firebase email-link activation.
- [x] No raw redemption URL is persisted or logged.
