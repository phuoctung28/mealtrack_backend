# RevenueCat existing-account recovery plan

Date: 2026-08-04

## Scope

- Keep the current web checkout/correlation architecture. No web repo work unless backend/mobile evidence shows a blocker.
- Preserve the duplicate-user safety guard. Do not auto-rebind an account from email alone.
- Keep raw redemption URLs memory-only on mobile and hash-only on backend.

## Verified current flow

- Web correlation is already hash-only and provider-verified: the BFF sends `app_user_id` + `redemption_link_hash`, backend stores the hash, and never returns a preflight token in the response. See `src/api/routes/v1/web_funnel.py:222-295`, `src/api/schemas/request/web_funnel_claim_requests.py:68-92`, `tests/unit/api/schemas/test_web_funnel_redemption_requests.py:11-30`, `tests/unit/api/routes/test_web_funnel_lead_routes.py:360-460`.
- Mobile deep links enter through `DeepLinkService`, which hands Redemption Links straight to `webPurchaseRedemptionCoordinatorProvider`, while the router holds the app on splash whenever the claim barrier is active. See `lib/core/di/providers/routing_providers.dart:72-95`, `lib/features/auth/presentation/router/app_router_redirect.dart:61-70`, `lib/main.dart:321-329`, `lib/main.dart:474-490`.
- The current automatic mobile path silently creates or reuses a Firebase user, aligns RevenueCat to that UID, redeems, then calls backend finalization. The provider uses `signInAnonymously()` when `currentUser` is null. See `lib/features/auth/application/providers/web_purchase_redemption_provider.dart:12-75`, `lib/features/auth/application/providers/web_purchase_redemption_provider.dart:89-102`, `lib/features/auth/application/services/web_purchase_redemption_coordinator.dart:143-167`, `lib/features/auth/application/services/web_purchase_redemption_coordinator.dart:322-367`, `test/features/auth/application/services/web_purchase_redemption_coordinator_test.dart:109-144`.
- Backend finalization already allows anonymous Firebase identities at the route boundary, then rejects any lead email already owned by a different Firebase UID. See `src/api/routes/v1/web_funnel.py:331-386`, `src/infra/services/web_funnel_redemption_completion.py:73-118`.
- Re-authenticated Google/Apple sign-in already performs RevenueCat `logIn(appUserId)` and `/users/sync`, while the claim barrier suppresses normal redirect churn during the sign-in. See `lib/features/auth/data/repositories/auth_repository.dart:375-425`, `lib/features/auth/application/providers/auth_flow_notifier.dart:163-220`.
- Existing account-protection is intentional elsewhere too: `/users/sync` maps email/UID collisions to a generic 409, and the repository converts identity unique-constraint races into `FirebaseIdentityConflictError`. See `src/app/handlers/command_handlers/sync_user_command_handler.py:40-52`, `src/api/routes/v1/users.py:120-127`, `src/infra/repositories/user_repository_async.py:118-128`, `tests/unit/api/routes/test_users_sync.py:17-39`, `tests/unit/infra/test_user_repository_async.py:24-47`.

## Smallest safe fix

### Phase 1: backend recovery contract only

- Keep `finalize_redemption()` as the authority for whether a lead can attach to a user.
- Add one machine-readable 409 branch for the specific case `email_owner.firebase_uid != uid` when the conflicting owner is still recoverable: same email owner, `onboarding_completed == false`, and no current `UserProfile`.
- Suggested response:

```json
{
  "detail": "Account identity could not be verified",
  "code": "existing_account_recovery_required"
}
```

- Do not include raw email, provider name, redemption URL, or lead identifiers in that error body.
- Keep all other conflicts generic. In particular:
  - existing completed profile -> stay generic 409
  - mismatched lead email -> stay generic 409
  - finalized under another UID or different idempotency key -> stay generic 409
- Backwards compatibility: old mobile builds will still see a 409 and fail closed; no schema migration required.

Files:

- `src/infra/services/web_funnel_redemption_completion.py`
- `tests/unit/infra/services/test_web_funnel_redemption_service.py` or a new focused completion test file if that existing file would become noisy

### Phase 2: Flutter in-place existing-account recovery

- Keep the anonymous auto path for true new buyers. Do not force sign-in up front.
- When backend finalization throws `existing_account_recovery_required` after a successful redemption:
  - keep the claim barrier active
  - keep `_hasRedeemed = true`
  - keep the same `_finalizationIdempotencyKey`
  - do not clear the accepted redemption state
  - transition from generic error into a recovery sign-in state on splash
- Recovery UX should reuse the existing Apple / Google / email options already shown for manual sign-in in `SplashScreen`; change the copy only for the recovery case.
- After the user signs in with the real existing account:
  - read the new Firebase identity
  - require verified email / non-anonymous identity
  - call `ensureRedemptionUserIdentified(newUid)` once more for determinism
  - call backend finalize again with the same idempotency key
  - do not call `preflight`
  - do not call `redeemWebPurchase` a second time
- Cancel should still sign out the temporary anonymous user if that user is still current, release the barrier, and discard in-memory redemption state.

Files:

- `lib/features/auth/application/providers/web_purchase_redemption_provider.dart`
- `lib/features/auth/application/services/web_purchase_redemption_coordinator.dart`
- `lib/features/auth/presentation/screens/splash_screen.dart`
- Optional only if needed for type plumbing: a small typed error helper in the same auth feature

### Phase 3: validation only

- Backend first, mobile second. No web deployment dependency.
- Staging validation must cover:
  - existing incomplete Google-owned account
  - brand-new buyer with no existing account
  - existing completed/profiled account that must stay blocked

## Data flow after the fix

1. Web checkout still correlates anonymous RevenueCat customer + redemption hash to the lead.
2. Mobile still auto-creates an anonymous Firebase UID and redeems immediately for brand-new buyers.
3. Backend finalization sees the lead email already belongs to another Firebase UID and returns `existing_account_recovery_required` instead of an undifferentiated 409.
4. Splash stays in the redemption barrier and asks the buyer to sign in with the already-owned Nutree account.
5. Standard auth flow signs the buyer into Firebase, logs RevenueCat into that UID, and runs `/users/sync`.
6. Coordinator re-aligns RevenueCat to the signed-in UID and retries backend finalize with the original idempotency key only.
7. Backend finalization now succeeds against the existing incomplete user, restores onboarding/profile/budget/subscription state, marks the lead claimed, and routes Home.

## Why this is the minimum change set

- No web changes.
- No schema changes.
- No raw redemption URL persistence.
- No automatic account merge by email.
- No second redemption call.
- No change to the happy path for new buyers.

## RevenueCat transfer gate

- This plan assumes the post-redeem sign-in can still resolve the same RevenueCat customer under the existing Firebase UID.
- RevenueCat’s current alias table says anonymous -> existing identified `logIn()` merges only when the target identified ID does not already have an anonymous alias; otherwise RevenueCat switches users without merge/transfer. Source: RevenueCat “Identifying Customers”, lines 501-531, opened 2026-08-04: https://www.revenuecat.com/docs/customers/identifying-customers
- That makes this a release gate, not a code assumption. We need staging proof for both:
  - existing UID with no prior anonymous alias
  - existing UID that may already have a prior alias/history
- If the second case does not merge, backend retry under the existing UID will likely 404 because the current RevenueCat subscriber will not resolve to the original web anonymous `original_app_user_id`. That would be a blocker for this minimal recovery path.

## Risks and mitigations

- High: recovery prompt shown for accounts that still cannot finalize.
  - Mitigation: backend emits `existing_account_recovery_required` only for incomplete users with no current profile; completed/profiled users stay on generic conflict.
- High: double redemption or mismatched finalization.
  - Mitigation: recovery path must never call `redeemWebPurchase` again and must reuse the original idempotency key. Current coordinator state already supports stable-key retry (`web_purchase_redemption_coordinator.dart:152`, `241-263`).
- High: startup/auth listeners hijack the recovery flow.
  - Mitigation: keep the existing claim barrier in place; router and auth validation already honor it. See `app_router_redirect.dart:68-69`, `auth_flow_notifier.dart:217-219`.
- Medium: process death after the first redeem loses in-memory recovery state.
  - Mitigation: accept this for v1 unless real-device testing reproduces it. If it does, add a tiny persisted recovery marker later that stores only the idempotency key + recovery mode, never the raw redemption URL.
- Medium: webhook timing divergence.
  - Mitigation: keep webhook handling as reconciliation only. Current backend already treats synchronous provider reads as authority and `PURCHASE_REDEEMED` as asynchronous evidence. See `src/infra/services/web_funnel_redemption_service.py:42-65`. RevenueCat’s webhook docs also state `PURCHASE_REDEEMED` fires when the deep link is opened and may be accompanied by `TRANSFER`, so it must not be the blocking access gate: https://www.revenuecat.com/docs/integrations/webhooks/event-types-and-fields

## Test matrix

### Backend

- Extend finalization service coverage for:
  - anonymous finalize -> `existing_account_recovery_required` on recoverable email-owner mismatch
  - anonymous finalize -> generic 409 when the conflicting owner is already completed/profiled
  - signed-in existing owner finalize -> succeeds without creating a second user row
  - finalized request replay with same UID + same idempotency key -> idempotent success
  - finalized request replay with different UID or different key -> 409 unchanged
- Keep current request/route coverage:
  - `tests/unit/api/schemas/test_web_funnel_redemption_requests.py`
  - `tests/unit/api/routes/test_web_funnel_lead_routes.py`
  - `tests/unit/infra/services/test_web_funnel_redemption_service.py`
  - `tests/unit/api/routes/test_users_sync.py`
  - `tests/unit/infra/test_user_repository_async.py`

### Flutter

- Extend `test/features/auth/application/services/web_purchase_redemption_coordinator_test.dart` for:
  - auto anonymous path enters recovery sign-in after recoverable 409
  - recovery sign-in finalizes with the same idempotency key and no second redeem
  - generic finalize conflict stays on error, not recovery
  - cancel after recovery-required error signs out the temporary anonymous user and clears the barrier
- Add focused provider coverage for parsing the new backend 409 code from Dio errors:
  - likely `test/features/auth/application/providers/web_purchase_redemption_provider_test.dart`
- Add one splash/widget test for the recovery CTA copy and actions if the UI text branches become non-trivial:
  - likely new `test/features/auth/presentation/screens/splash_screen_redemption_test.dart`

## Rollout and rollback

- Rollout order:
  1. backend contract + tests
  2. Flutter recovery flow + tests
  3. staging validation on the concrete failing scenario
- Rollback:
  - backend: remove the structured 409 code path; no data rollback needed
  - mobile: remove the recovery branch and fall back to the current generic error path
  - because there is no schema migration and no raw-URL persistence, rollback is code-only

## Done when

- The August 4, 2026 staging failure pattern can finish under the existing Google Firebase UID instead of the new anonymous UID.
- No new `users` row is created for that recovery.
- The redemption is not consumed twice.
- The same idempotency key is reused across the failed anonymous finalize and the successful recovered finalize.
- The buyer lands on Home after successful recovery.
- A completed/profiled existing account is still protected from snapshot overwrite.
- No raw redemption URL is logged, persisted, or returned.

## Unresolved questions

- Does the staging Google UID already have an existing RevenueCat customer history or anonymous alias that would trigger RevenueCat’s no-merge branch?
- Is in-memory-only recovery acceptable for v1, or do we need restart-resume durability after the first redemption succeeds but pre-finalization recovery is still pending?
