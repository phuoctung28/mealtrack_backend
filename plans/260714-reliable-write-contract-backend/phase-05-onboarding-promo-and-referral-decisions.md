---
phase: 5
title: "Onboarding Promo and Referral Decisions"
status: pending
priority: P1
dependencies: [0, 1, 2]
effort: "3-5 engineering days plus product approval"
---

# Phase 5: Onboarding, Promo, and Referral Decisions

## Overview

Make purchase-finalization writes convergent while preserving legacy calls.
This phase records product choices explicitly; every unresolved choice defaults
to capability disabled and no automatic retry.

## Current Evidence

| Action | Current implementation | Existing guard/gap |
|---|---|---|
| Onboarding complete | `PUT /v1/users/firebase/{firebase_uid}/onboarding/complete`; `CompleteOnboardingCommandHandler` | Set-if-false; repeat returns `updated=false`; handler creates concrete UoW; no operation result test |
| Promo redeem | `POST /v1/promo-codes/redeem`; direct `RedeemPromoCodeCommandHandler` | Row lock + unique promo/user; repeat returns 422 instead of original success |
| Referral apply | `POST /v1/referrals/apply`; direct `ApplyReferralCodeCommandHandler` | Internal conversion is user-unique, but affiliate path only has an outbox row; two affiliate codes can both enqueue |
| Referral payout | `POST /v1/referrals/payout` | Only pending-status guard; no operation lookup; excluded |
| Referral my-code | write-on-read GET | Lazy random code creation; excluded |

Promo/referral routes currently instantiate handlers directly instead of using
the configured PyMediator singleton. Refactor them through commands registered at
`src/api/dependencies/event_bus.py`; handlers receive injected fresh UoWs.

## Proposed Decisions and Safe Defaults

| Decision needing approval | Proposed v1 contract | Fail-closed default |
|---|---|---|
| Onboarding repeat | Operation-aware request returns stored result; a new operation after already complete returns 200 `already_completed` | Flag off; legacy set-if-false only |
| Promo same code/user, new operation | 200 success with `outcome=already_redeemed`; never increments usage twice | Flag off; preserve current 422 legacy behavior |
| Referral same user/code/source, new operation | 200 success with `outcome=already_applied`; no second conversion/outbox event | Flag off; preserve current 400 legacy behavior |
| Referral same user, different code or internal/affiliate source | 409 `REFERRAL_ALREADY_ASSIGNED`; the first attribution/benefit is immutable | Flag off; no automatic retry |
| Affiliate validation unavailable | Leave operation pending/retryable only through lookup + explicit application retry; never fall through to a different benefit | Capability off until fault tests pass |
| Payout idempotency/status | Separate future contract with payout ID and status route | Not advertised; always `neverAutoRetry` |
| Lazy my-code creation | Separate concurrency-safe create/read decision | Not advertised as a safe GET |

Approval owners: product owns benefit semantics and attribution immutability;
backend owns transaction/error/status contracts; mobile owns UX and retry enablement.
No flag turns on until all three accept fixtures.

## Request and Response Compatibility

- Onboarding adds an optional request model in
  `src/api/schemas/request/user_requests.py` containing `client_operation_id`;
  its response model is in `src/api/schemas/response/user_responses.py`. No-body
  old calls remain valid. The route resolves both
  verified Firebase path ownership and internal user ID for operation scoping.
- Promo/referral existing request bodies add optional `client_operation_id`.
  Referral fingerprint fixtures include the normalized `discount_applied` integer
  and uppercase `currency`; changing either with the same operation ID conflicts.
- All require matching `Idempotency-Key` when operation-aware.
- Preserve existing fields and statuses for legacy requests. Operation-aware
  responses add `client_operation_id`, `outcome`, and `replayed`; old decoders
  may ignore additions. Duplicate same-operation returns original status/body.
- Generic operation lookup is the reconciliation/status route. It returns only
  safe outcome metadata, never raw promo/referral code or Firebase UID.

## Related Code Files

| Area | Paths |
|---|---|
| Onboarding route/schema | `src/api/routes/v1/users.py`, `src/api/schemas/request/user_requests.py`, `src/api/schemas/response/user_responses.py` |
| Onboarding command/handler | `src/app/commands/user/complete_onboarding_command.py`, `src/app/handlers/command_handlers/complete_onboarding_command_handler.py` |
| Promo route/command/handler | `src/api/routes/v1/promo_codes.py`, `src/app/commands/promo_code/redeem_promo_code_command.py`, `src/app/handlers/command_handlers/promo_code/redeem_promo_code_handler.py` |
| Promo repository/models | `src/infra/repositories/promo_code_repository.py`, `src/infra/database/models/promo_code/promo_code.py`, `src/infra/database/models/promo_code/promo_code_redemption.py` |
| Referral route/command/handler | `src/api/routes/v1/referrals.py`, `src/app/commands/referral/apply_referral_code_command.py`, `src/app/handlers/command_handlers/referral/apply_referral_code_handler.py` |
| Referral repository/models | `src/infra/repositories/referral_repository.py`, `src/infra/database/models/referral/referral_code.py`, `src/infra/database/models/referral/referral_conversion.py`, new `src/infra/database/models/referral/referral_attribution.py` |
| Affiliate adapter/outbox | `src/infra/adapters/affiliate_service_adapter.py`, `src/domain/ports/affiliate_service_port.py`, `src/infra/repositories/affiliate_event_outbox_repository.py`, `src/infra/database/models/affiliate_event_outbox.py`, `src/infra/services/affiliate_outbox_dispatch_service.py`, `src/cron/affiliate_outbox.py` |
| Composition | `src/api/dependencies/event_bus.py` |
| Existing tests | `test_redeem_promo_code_handler.py`, `test_promo_code_repository.py`, `test_apply_affiliate_code_handler.py`, mocked route tests |
| New tests | `tests/unit/api/test_reliable_purchase_finalization_routes.py`, `tests/integration/api/test_reliable_purchase_finalization_writes.py` |

## Implementation Steps

1. Pin legacy status/body behavior, then add operation-aware red tests.
2. Convert promo/referral commands to normal CQRS `Command` types and register
   handlers. Remove direct route handler construction.
3. Refactor all three handlers to injected `AsyncUnitOfWorkPort`; repositories
   flush only and UoW owns commit/rollback.
4. Onboarding: lock/read user, apply final state if needed, insert a unique
   operation-scoped cache-invalidation effect, and write the exact response in
   the same UoW. The effect dispatcher invalidates after commit and repairs a
   crash; route/handler code performs no untracked post-commit invalidation.
5. Promo: keep promo row lock; handle unique business duplicate according to
   operation-aware decision without incrementing `current_uses`.
6. Referral: normalize the presented code and compute a server-keyed HMAC. For
   internal codes, resolve the owning referral row; for affiliate codes, call
   `AffiliateServicePort.validate_code` after reservation but outside the
   mutation transaction. Provider timeout/unavailability leaves the operation
   pending and performs no local claim; it never falls through to internal or a
   different benefit.
7. In the fenced mutation UoW, claim `referral_attributions` with unique
   `referred_user_id`. The row stores source, code HMAC, and stable internal or
   affiliate reference but no raw code. Same source/HMAC maps to
   `already_applied`; any other existing row finalizes safe 409. For an internal
   winner, insert `ReferralConversion`; for an affiliate winner, enqueue one
   `AffiliateEventOutbox` linked by an explicit `attribution_id`/unique event key.
   Attribution, conversion/outbox, exact response, and operation finalization
   commit together. Outbox payload JSON is never the deduplication key.
8. Record only outcome/business row ID in snapshots; exclude code, discount,
   currency, Firebase UID, affiliate ID, and outbox payload.
9. Keep payout and my-code absent from manifest and document their no-retry policy.

## Test Scenario Matrix

| Scenario | Expected |
|---|---|
| Onboarding same operation | Original `updated` result replayed |
| Onboarding new operation after complete | Approved `already_completed` outcome |
| Concurrent promo same code/user | One redemption/use increment |
| Promo timeout after commit | Lookup committed; no second increment |
| Referral same user/code | One conversion/outbox event |
| Same operation/code, changed discount or currency | 409 fingerprint conflict; no benefit mutation |
| Referral same user/different code | Deterministic 409, no reassignment |
| Concurrent internal vs affiliate codes | One attribution winner; loser 409; one benefit effect |
| Concurrent two affiliate codes | One attribution/outbox winner independent of JSON payload |
| Same affiliate code after outbox dispatch crash | `already_applied`; idempotent linked outbox repair |
| Affiliate adapter transient failure | No local conversion; operation not falsely committed |
| Account switch/other user lookup | `notFound`; no benefit metadata leak |

## Verification Commands

```bash
uv run pytest tests/unit/handlers/test_redeem_promo_code_handler.py tests/unit/repositories/test_promo_code_repository.py tests/unit/app/handlers/command_handlers/referral/test_apply_affiliate_code_handler.py
uv run pytest tests/unit/api/test_reliable_purchase_finalization_routes.py
uv run pytest tests/integration/api/test_reliable_purchase_finalization_writes.py -o addopts="" -m integration
```

## Success Criteria

- [ ] Product/backend/mobile approvals are recorded against response fixtures.
- [ ] Onboarding, promo, and referral effects commit with exact durable responses.
- [ ] Business-key duplicates cannot increment, reassign, or enqueue twice.
- [ ] Unique referred-user attribution spans internal and affiliate paths and is
  enforced by PostgreSQL, not handler timing or outbox JSON.
- [ ] Payout and lazy my-code remain explicitly unsupported.

## Risks and Security

Changing duplicate errors to success can affect analytics and support flows, so
it applies only to enabled operation-aware requests until approved. Never log
codes, discount/currency, UIDs, affiliate identity, or operation identifiers.
