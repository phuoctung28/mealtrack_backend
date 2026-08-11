---
phase: 4
title: "Web cleanup"
status: complete
effort: ""
---

# Phase 4: Web cleanup

## Overview

Retain web checkout and anonymous RevenueCat correlation while removing copy and
fallbacks that describe the retired passwordless activation flow.

## Implementation Steps

1. Keep the web checkout outside the mobile app and keep the Redemption Link email.
2. Update `/redeem` and success copy to instruct Google/Apple sign-in in the app.
3. Remove or gate stale email-link/custom-token activation handoff code from active routes.
4. Preserve staging/production host allowlists and raw-token redaction.

## Success Criteria

- [x] Web never authenticates Firebase or grants access.
- [x] Web copy does not mention passwordless/email-link activation.
- [x] Checkout correlation tests and build pass.
