# Phase 05: RevenueCat And External Trust Boundaries

## Context Links

- [Plan overview](./plan.md)
- [Security threat model](./reports/security-threat-model.md)
- `src/api/dependencies/auth.py`
- `src/api/routes/v1/webhooks.py`

## Overview

**Priority:** P2
**Status:** Planned

This phase does not execute a broad premium guard or admin gate rollout.
RevenueCat remains the source of truth for subscription state. The phase only
documents and preserves external trust boundaries when those areas are touched.

## Key Insights

- Firebase auth and existing admin dependencies exist, but they are not the work
  for this plan.
- RevenueCat handles subscription lifecycle and entitlement source-of-truth
  status.
- RevenueCat and affiliate integrations cross external trust boundaries.
- File/image URLs and IDs are attacker-controlled until scoped and verified.

## Requirements

- Every user-owned read/write proves `user_id` ownership.
- Do not add broad admin or premium enforcement work in this plan.
- If a touched route already has an admin/auth/subscription pattern, preserve
  the existing behavior.
- Webhooks and affiliate calls verify signatures/secrets before mutation.
- Logs avoid secrets, tokens, payout details, and raw food payloads.

## Architecture

Trust boundaries:

```text
client -> Firebase auth -> API -> CQRS handler -> user-owned repository query
RevenueCat -> webhook secret -> subscription mutation
MealTrack -> HMAC signed request -> nutree-affiliate
client image/url -> scoped storage check -> server fetch/mutation
```

## Related Code Files

Review:
- `src/api/dependencies/auth.py`
- `src/api/routes/v1/webhooks.py`
- `src/infra/adapters/affiliate_service_adapter.py`
- `src/api/routes/v1/meal_upload_token.py`
- `src/api/routes/v1/meal_scan_by_url.py`
- User-owned handlers/repositories touched by future features

## Implementation Steps

1. For touched external-boundary areas, identify whether the input is client,
   RevenueCat, affiliate, image URL, or operator controlled.
2. Verify ownership checks happen before returning or mutating user-owned data.
3. Verify RevenueCat webhook secret and affiliate HMAC behavior when those flows
   are touched.
4. Verify image URL/upload-token scope checks when image flows are touched.
5. Add negative-path tests only for the touched boundary.

## Todo List

- [ ] Classify touched external-boundary inputs.
- [ ] Verify ownership checks.
- [ ] Preserve RevenueCat-backed subscription behavior.
- [ ] Verify webhook, affiliate, or image-boundary checks when touched.
- [ ] Verify log redaction.
- [ ] Add scoped negative-path tests.

## Success Criteria

- No route silently relies on client-side enforcement.
- No broad premium/admin scope is introduced.
- RevenueCat remains the subscription source of truth.
- Security assumptions are captured in the feature docs or PR.

## Risk Assessment

- High for payment, affiliate, payout, and image flows.
- Mitigation: threat-model before implementation and add negative-path tests.

## Security Considerations

Use the threat model report as the starting point for external-boundary attacker
stories. Do not broaden data access to simplify handlers.

## Next Steps

Run this phase before touching affiliate, payout, webhook, or image upload
features. Skip it for unrelated feature work.
