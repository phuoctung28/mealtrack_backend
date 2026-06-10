# Phase 4 Report: Promo and Referral UoW Slice

## Summary

- Promoted promo-code and referral repositories into `AsyncUnitOfWork`.
- Runtime promo/referral handlers now use `uow.promo_codes` and `uow.referrals`.
- Webhook referral credit/revoke helpers now use the same UoW-owned referral repository.
- Handler unit tests now fake the UoW boundary instead of patching repository constructors.

## Files Changed

- `src/infra/database/uow_async.py`
- `src/domain/ports/async_unit_of_work_port.py`
- `src/app/handlers/query_handlers/promo_code/validate_promo_code_handler.py`
- `src/app/handlers/command_handlers/promo_code/redeem_promo_code_handler.py`
- `src/app/handlers/query_handlers/codes/validate_code_handler.py`
- `src/app/handlers/command_handlers/referral/apply_referral_code_handler.py`
- `src/app/handlers/command_handlers/referral/request_payout_handler.py`
- `src/app/handlers/query_handlers/referral/validate_referral_code_handler.py`
- `src/app/handlers/query_handlers/referral/get_my_referral_code_handler.py`
- `src/app/handlers/query_handlers/referral/get_referral_stats_handler.py`
- `src/api/routes/v1/webhooks.py`
- `tests/unit/handlers/test_validate_promo_code_handler.py`
- `tests/unit/handlers/test_redeem_promo_code_handler.py`
- `tests/unit/handlers/test_validate_code_handler.py`
- `tests/architecture/test_async_db_runtime_boundaries.py`

## Verification

- `pytest tests/unit/handlers/test_validate_promo_code_handler.py tests/unit/handlers/test_redeem_promo_code_handler.py tests/unit/handlers/test_validate_code_handler.py tests/unit/handlers/command_handlers/test_request_payout_validation.py tests/unit/infra/database/test_uow_async.py tests/architecture/test_async_db_runtime_boundaries.py -q`
  - Result: 44 passed.
- `ruff check` on touched promo/referral/UoW files.
  - Result: all checks passed.
- Expanded async consolidation regression bundle with promo/referral handler tests.
  - Result: 274 passed, 3 warnings.

## Boundary

Static runtime search found no direct `PromoCodeRepository` or `ReferralRepository` imports/constructors under `src/app`, `src/api`, `src/cron`, or `src/infra/services` after this slice.

## Unresolved Questions

None.
