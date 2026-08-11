---
phase: 2
title: "Backend finalization"
status: complete
effort: ""
---

# Phase 2: Backend finalization

## Overview

Make backend finalization attach a verified web purchase to the authenticated
Firebase account without duplicating profiles or subscriptions.

## Implementation Steps

1. Require a fresh verified non-anonymous Firebase identity for finalization.
2. Verify the provider customer and active standard entitlement server-side.
3. Resolve the lead by the provider-bound redemption binding, not client email.
4. Support an existing owner with the matching normalized email without creating a second profile.
5. Make repeated finalization after a committed result return the stored result for the same binding/UID.
6. Persist web purchases as `platform=web` with provider dates/store metadata.
7. Add regression tests for ownership, retries, concurrency, refund state, and environment mismatch.

## Success Criteria

- [x] New and existing authenticated accounts finalize successfully.
- [x] Wrong Firebase account is rejected without disclosure.
- [x] App restart after a committed finalization can recover access.
- [x] No duplicate profile, weekly budget, or subscription is created.
