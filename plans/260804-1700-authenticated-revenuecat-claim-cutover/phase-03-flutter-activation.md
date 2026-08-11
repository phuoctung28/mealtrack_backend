---
phase: 3
title: "Flutter activation"
status: complete
effort: ""
---

# Phase 3: Flutter activation

## Overview

Use a dedicated activation screen that authenticates the user before consuming
the RevenueCat Redemption Link and routes directly to Home on success.

## Implementation Steps

1. Keep cold-start and warm-start deep-link intake with the claim barrier.
2. Add Google and Apple sign-in actions to the activation screen.
3. Do not call `redeemWebPurchase()` until a stable, verified Firebase UID exists.
4. Redeem, finalize, refresh auth/subscription state, and route Home.
5. Preserve the finalization idempotency key through retries and recover committed results after restart.
6. Remove active Firebase email-link and anonymous activation UI from this flow.
7. Map backend/provider errors to actionable copy and never leave an infinite spinner.

## Success Criteria

- [x] A new buyer reaches Home after Google/Apple sign-in.
- [x] Existing account activation preserves the existing profile.
- [x] Wrong-account, expired, consumed, timeout, and retry states are actionable.
- [x] Flutter analyze and focused tests pass.
