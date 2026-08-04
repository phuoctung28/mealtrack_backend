---
title: "Passwordless RevenueCat Redemption Handoff"
description: "Resume a RevenueCat redemption from normal Firebase email-link sign-in across backend, Flutter, and web funnel."
status: complete-local-validation-pending-staging
priority: P1
branch: "feature/revenuecat-anonymous-redemption-sit"
tags: [revenuecat, firebase-auth, email-link, flutter, web-funnel]
---

# Passwordless RevenueCat Redemption Handoff

## Contract

The web checkout captures the canonical email and correlates an anonymous
RevenueCat customer using only a SHA-256 redemption-link digest. After checkout,
the web funnel navigates to `/postcheckout`. The buyer opens the RevenueCat link
in the app, continues through the normal passwordless Firebase email-link sign-in
flow, and the app silently resumes redemption after Firebase returns the verified
UID. Backend finalization remains the access authority.

## Phases

| Phase | Repository | Scope | Status |
|---|---|---|---|
| 1 | Backend | Accept verified email-link identities; preserve matching email, idempotency, and expiry-safe finalization | complete |
| 2 | Flutter | Restore normal email-link auth integration; retain redemption across auth/cold start; remove activation UI | complete |
| 3 | Web funnel | Add `/postcheckout` guidance and route successful checkout there | complete |
| 4 | All | Focused tests, analyzers/builds, docs, and staging checklist | local complete; staging pending |

## Acceptance criteria

- Normal mobile startup/auth remains the visible UX; no redemption activation screen.
- A pending redemption resumes only after a verified Firebase email identity matches checkout email.
- Firebase email-link expiry can be retried without losing the pending redemption.
- RevenueCat redemption expiry clears the pending capability and never grants Premium; the user receives recovery guidance.
- A successful redemption finalizes once, preserves existing profiles, refreshes entitlement, and routes Home.
- Raw redemption URLs remain out of backend persistence, logs, analytics, and ordinary preference storage.
- Web checkout success navigates to `/postcheckout` without granting access in the browser.

## Out of scope

- Direct Paddle `transaction.completed` webhooks.
- Re-enabling legacy custom-token/magic-claim endpoints.
- Replacing native RevenueCat purchases or changing product/entitlement mappings.
- Automatic provider-side redemption-email resend unless a verified provider API is available.

## Validation

- Backend focused tests and Ruff.
- Flutter focused auth/redemption tests and analyzer.
- Web tests and production build.
- Staging validation for same-device, cold-start, wrong-email, Firebase-link expiry,
  RevenueCat-link expiry, retry, and existing-account journeys.
