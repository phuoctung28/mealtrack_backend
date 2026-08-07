# RevenueCat anonymous redemption finalization

Date: 2026-08-04

## Goal

Make RevenueCat Redemption Links redeem through the RevenueCat SDK first, then
bind the purchase to the authenticated Firebase user and finalize Nutree access.

## Status

- Backend diff covers provider-alias storage, preflight binding guardrails, and
  the existing-account sign-in recovery path.
- Flutter diff covers RevenueCat-first redemption, Firebase sign-in recovery,
  backend finalization retry, and the updated splash-state flow.
- Code review and local verification are complete; sandbox/device proof still
  needs to run before release closure.
- Plan remains pending until those verification gates clear.

## Scope

- Backend: never treat RevenueCat provider aliases as Firebase `redeemer_uid`.
- Flutter: do not create or align a Firebase anonymous UID before
  `Purchases.redeemWebPurchase()`.
- Flutter: after Firebase authentication, call RevenueCat `logIn(firebaseUid)`
  and retry the existing idempotent backend finalization.
- Preserve existing Google, Apple, and email sign-in recovery behavior.
- Keep the web funnel unchanged; its lead and RevenueCat correlation contracts
  already provide the provider-side redemption binding.

## Acceptance criteria

1. A fresh redemption calls RevenueCat redemption before Firebase identity
   alignment when no stable Firebase user is signed in.
2. A successful RevenueCat redemption followed by Firebase sign-in finalizes
   the local Nutree subscription and routes to Home.
3. A RevenueCat `PURCHASE_REDEEMED` webhook stores provider aliases but never
   assigns an alias to `redeemer_uid`.
4. Existing incorrect webhook bindings cannot block a new authenticated UID
   in the code path; the already-corrupted staging row requires a separate
   data repair or a fresh purchase.
5. Finalization remains server-authoritative, idempotent, and fail-closed for
   inactive or mismatched RevenueCat customers.

## Files

- Modify `src/infra/services/web_funnel_redemption_service.py`.
- Modify its focused unit tests.
- Modify `lib/features/auth/application/services/web_purchase_redemption_coordinator.dart`.
- Modify `lib/features/auth/application/providers/web_purchase_redemption_provider.dart`
  only if dependency wiring must change.
- Update Flutter coordinator tests for ordering and retry behavior.

## Verification

- Backend focused pytest and lint/type checks for changed modules.
- Flutter focused coordinator tests, `flutter analyze`, and relevant build
  compilation checks where available.
- Confirm web funnel tests remain unchanged and passing.

## Out of scope

- No database migration.
- No new preflight credential or endpoint.
- No email-based RevenueCat App User ID.
- No automatic account merge based only on matching email.
- No provider-side RevenueCat/Paddle configuration change.
