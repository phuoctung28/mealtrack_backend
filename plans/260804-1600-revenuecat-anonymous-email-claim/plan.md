# RevenueCat Anonymous Email Claim

## Decision

Use RevenueCat's redemption link as the purchase/email possession proof. Do not send a second Firebase passwordless email and do not use the checkout email as a RevenueCat App User ID or access credential.

## Flow

1. Web creates an anonymous RevenueCat checkout and correlates the redemption-link digest with the lead.
2. RevenueCat sends the redemption link to the checkout email.
3. The user opens the link in the mobile app.
4. Flutter ensures a Firebase anonymous session, identifies RevenueCat with that Firebase UID, and calls `Purchases.redeemWebPurchase()`.
5. Flutter calls backend finalization with the Firebase anonymous ID token.
6. Backend verifies the RevenueCat subscriber and active entitlement, claims the correlated lead, creates the paid profile/subscription, refreshes auth/subscription state, and routes to Home.

## Security boundaries

- The raw RevenueCat redemption URL remains in memory and is never sent to or stored by the backend.
- Backend entitlement verification remains authoritative; web callbacks and RevenueCat webhooks only correlate/reconcile state.
- Firebase anonymous UID is the session identity. Email is copied from the paid lead for the profile but is not trusted from the client and is not used to select a claim.
- Existing fully onboarded accounts are not silently merged by email. They receive a clear conflict and must use the normal account sign-in path.
- The legacy preflight/email-link path is not used by the new mobile flow.

## Repository scope

- `mealtrack_backend`: keep anonymous finalization/provider alias matching safe and add regression tests for the anonymous path and existing-account conflict.
- `nutree_ai`: remove Firebase email-link activation and Google/Apple activation choices; implement anonymous-session activation and a progress/error/retry screen.
- `nutree_web_funnel`: no runtime change expected; retain anonymous checkout, redemption-link digest correlation, and RevenueCat email handoff. Validate its tests/build only.

## Acceptance criteria

- A fresh staging buyer can open the RevenueCat email link, activate without another email being sent, and land on Home.
- Retry after a transient backend/provider failure is idempotent and does not charge again.
- A missing/expired/invalid redemption link fails with a recoverable message.
- An existing onboarded Firebase account is not overwritten or merged automatically.
- Flutter has no call to `sendSignInLinkToEmail` in the redemption path and no activation UI for Google/Apple.
- Backend and Flutter focused tests pass; Flutter analyze and staging no-codesign build pass; web lint/test/build remain green.
