---
title: "Authenticated RevenueCat Claim Cutover"
description: "Replace anonymous/passwordless claim activation with authenticated Google/Apple-first RevenueCat redemption and remove stale handoff paths."
status: in-progress
priority: P1
branch: "feature/revenuecat-anonymous-redemption-sit"
tags: [revenuecat, firebase-auth, flutter, web-funnel, staging]
blockedBy: []
blocks: []
created: "2026-08-04T13:40:55.988Z"
createdBy: "ck:plan"
source: skill
---

# Authenticated RevenueCat Claim Cutover

## Overview

The buyer completes checkout on the web, opens the RevenueCat Redemption Link in
Flutter, signs in with the Google or Apple account used at checkout, and only
then redeems the purchase and finalizes the subscription against that stable
Firebase UID. Anonymous activation, Firebase email-link activation, Hosting
fallbacks, and legacy claim UI are removed or disabled from this path.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Contract and cleanup](./phase-01-contract-and-cleanup.md) | Complete |
| 2 | [Backend finalization](./phase-02-backend-finalization.md) | Complete |
| 3 | [Flutter activation](./phase-03-flutter-activation.md) | Complete |
| 4 | [Web cleanup](./phase-04-web-cleanup.md) | Complete |
| 5 | [Verification](./phase-05-verification.md) | In progress |

## Dependencies

- RevenueCat web checkout/correlation remains enabled for SIT.
- Flutter TestFlight build is required for device validation after code changes.
- No Firebase Hosting or passwordless-email configuration is required.

## Acceptance Criteria

- New buyer: checkout → Redemption Link → Google/Apple sign-in → redeem → backend finalize → Home.
- Existing buyer: same flow attaches the purchase without overwriting the existing profile.
- Wrong account, expired link, already-claimed link, refunded purchase, and transient failures have distinct recoverable states.
- Backend finalization is safe across retries and app restarts.
- Web copy no longer promises Firebase email-link activation.
- Legacy anonymous/email-link claim paths cannot be selected by the active UI.
