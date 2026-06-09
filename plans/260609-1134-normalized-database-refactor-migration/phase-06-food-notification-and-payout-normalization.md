---
phase: 6
title: "Food notification and payout normalization"
status: completed
priority: P2
effort: "1-2 weeks"
dependencies: [1, 2]
---

# Phase 6: Food notification and payout normalization

## Context Links

- Food model: `src/infra/database/models/food_reference_model.py`
- Notification models: `src/infra/database/models/notification/`
- Referral/payout models: `src/infra/database/models/referral/`

## Overview

Normalize remaining source-of-truth JSON where it affects search/support/workflow: food reference serving details, notification send context, and payout payment details.

## Key Insights

- `food_reference.serving_sizes` and `extra_nutrients` are JSON but drive food lookup and nutrition support.
- `notifications.context` is acceptable as immutable render snapshot, but recipient/token truth should stay normalized.
- `payout_requests.payment_details` is sensitive and can become operational workflow data.

## Requirements

- Functional: food search and lookup responses remain stable.
- Functional: notification dispatch uses normalized token ownership, not context as source of truth.
- Functional: payout workflow fields used by support/admin become typed or encrypted normalized rows.
- Non-functional: do not over-normalize raw provider snapshots that are not queried.

## Architecture

Food catalog:

- `food_reference_serving_sizes(food_reference_id, name, grams, milliliters, is_default, position)`
- `food_reference_nutrients(food_reference_id, nutrient_key, amount, unit)`

Notifications:

- keep `notifications.context` as render snapshot only;
- optionally add `notification_recipients(notification_id, user_fcm_token_id, status, provider_message_id, sent_at)` if dispatch needs per-token audit.

Payout:

- add typed fields needed for workflow (`payment_account_type`, masked destination, country/currency if relevant);
- move sensitive detail payload to encrypted field/table only if currently required.

## Related Code Files

| Action | File |
|---|---|
| Modify | `src/infra/database/models/food_reference_model.py` |
| Create | `src/infra/database/models/food_reference_serving_size.py` |
| Create | `src/infra/database/models/food_reference_nutrient.py` |
| Modify | `src/infra/repositories/food_reference_repository.py` |
| Modify | `src/infra/database/models/notification/notification.py` |
| Create | `src/infra/database/models/notification/notification_recipient.py` if needed |
| Modify | `src/infra/repositories/notification_repository_async.py` |
| Modify | `src/infra/database/models/referral/payout_request.py` |
| Modify | `src/infra/repositories/referral_repository.py` |
| Create | `migrations/versions/YYYYMMDDHHMMSS_normalize_food_notification_payout_details.py` |
| Modify/Add | `tests/unit/infra/repositories/test_food_reference_repository.py` |
| Modify/Add | `tests/unit/infra/test_cron_notification_dispatch_service.py` |
| Modify/Add | `tests/unit/repositories/test_promo_code_repository.py` or referral repository tests |

## Implementation Steps

1. Food tests before: barcode lookup, search, batch normalized-name lookup, and serving-size projection.
2. Add food serving/nutrient child tables and backfill from JSON fields.
3. Update food repository to dual-write child rows and legacy JSON.
4. Notification tests before: dispatch reads active tokens from `user_fcm_tokens`, context remains render snapshot.
5. Add `notification_recipients` only if per-token status/audit is required now. Otherwise document context exception and skip table.
6. Payout tests before: request payout, pending payout lookup, admin/support fields.
7. Add typed payout fields and constraints for status/payment method. Do not log raw payment details.
8. Backfill typed payout fields from JSON where possible; retain JSON temporarily or replace with encrypted sensitive payload after security review.

## Test Scenario Matrix

| Scenario | Test |
|---|---|
| Food reference JSON backfills to child rows | migration test |
| Food lookup returns same shape after normalized read | repository test |
| Notification send path does not trust context tokens | cron/dispatch test |
| Payout status/method rejects invalid values | DB/repository test |
| Sensitive payout details are not logged | unit log assertion if practical |

## Success Criteria

- [x] Food serving sizes and nutrients are queryable without JSON parsing.
- [x] Notification context is documented as snapshot, not source of recipient truth.
- [x] Payout workflow fields have constraints and typed columns.
- [x] JSON that remains has explicit raw/snapshot/security reason.

## Risk Assessment

Medium. Food and notification changes can be scoped safely. Payout touches sensitive data and may require product/legal retention decision before contracting JSON.

## Security Considerations

Payout details are sensitive. Prefer masking, encryption, least-privilege access, and no raw payload logging.

## Next Steps

After normalized writes are stable, cut over reads, add final indexes, and only then contract legacy columns.
