---
phase: 5
title: "Verification"
status: in-progress
effort: ""
---

# Phase 5: Verification

## Overview

Verify contracts, regression behavior, and deployment readiness across all three
repositories without claiming real-device/provider success from unit tests alone.

## Implementation Steps

1. Run backend focused pytest, Ruff, and type checks for changed modules.
2. Run Flutter focused tests and `flutter analyze`.
3. Run web lint, Vitest, and production build.
4. Inspect OpenAPI and staging logs for the authenticated finalize request.
5. Perform a real TestFlight sandbox test with a new email and an existing account.

## Success Criteria

- [x] Automated checks pass in each repository.
- [ ] Staging logs show `200` finalization followed by Home access.
- [x] No new passwordless email or anonymous-finalization request appears in local tests.
- [x] Remaining provider/store limitations are documented separately.
