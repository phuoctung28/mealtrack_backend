---
title: "Red Team Review"
type: report
status: complete
created: 2026-07-02
---

# Red Team Review

## Findings

1. Cancelled trial users are excluded from current push/email expiry queries.
   - Evidence: cancellation sets `status='cancelled'` while access remains until `expires_at`; expiry queries filter `status='active'`.
   - Resolution: Phase 2 adds an eligibility query for active and cancelled-but-unexpired trials.

2. PostHog winback email can duplicate backend Resend cancellation email if stale webhook code remains enabled.
   - Evidence: backend sends cancellation email inside `handle_cancellation`; user confirmed lifecycle email cron is disabled separately.
   - Resolution: Phase 3 makes PostHog the intended owner and gates/removes the webhook email path.

3. "Haven't claimed offer" is not currently a server-side fact.
   - Evidence: mobile has local `discountOfferSeenKey`; backend does not track discounted purchase claim.
   - Resolution: Phase 1 adds durable claim state from RevenueCat-confirmed purchase fields.

4. Hardcoding VND 299k is wrong outside Vietnam and risky even in Vietnam if store price changes.
   - Evidence: mobile already gets price strings from RevenueCat packages.
   - Resolution: Phase 4 uses RevenueCat localized product prices only.

5. RevenueCat webhook may not expose offering ID.
   - Risk: implementation could silently fail to mark claims.
   - Resolution: Phase 1 requires sandbox payload verification and supports product ID or discount identifier config.

6. Push copy can drift into promotional messaging.
   - Risk: Apple guideline 4.5.4 requires explicit marketing push opt-in and opt-out.
   - Resolution: Phase 2 keeps push as service reminder; discount/price appears on paywall or email.

7. Mobile `offeringId` seam is currently dead.
   - Evidence: screen constructors accept `offeringId`, but no usage found beyond field assignment.
   - Resolution: Phase 4 wires a scoped offering override into `paywallProvider`.

8. Backend docs mention T-2d/T-1d, but code schedules one `trial_expiry_1d` row.
   - Resolution: Phase 5 updates docs to match the implemented timing.

## Whole-Plan Consistency Sweep

- Files checked: `plan.md`, all five phase files after drafting.
- Decision deltas: service push no price, server-side claim, include cancelled-unexpired trials, single email owner, RevenueCat localized price.
- Unresolved contradictions: none after phase mapping.
