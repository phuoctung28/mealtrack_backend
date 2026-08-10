# OpenAI Translation Service TDD Validation

Date: 2026-08-09

## Scope

- `lint-imports`
- `tests/architecture/test_async_db_runtime_boundaries.py`
- translation-focused unit tests
- translation integration smoke
- CI-aligned unit suite: `uv run --python 3.13.2 pytest tests/unit --cov=src --cov-fail-under=65`

## Results Overview

- `lint-imports`: passed
- Translation-focused unit tests: 81 passed
- Translation integration smoke: 1 skipped
- Architecture tests: 13 passed, 1 failed
- Full unit suite: 2231 passed, 0 failed, 44 warnings
- Coverage: 79.33% line coverage, threshold 65% reached
- Focused Ruff for new adapter/fixture/translation-service files: passed
- Repository-wide Ruff/format checks: not green on pre-existing baseline debt

## Passed Commands

- `uv run --python 3.13.2 lint-imports`
- `uv run --python 3.13.2 pytest tests/architecture/test_layer_boundaries.py::TestDomainLayerBoundaries tests/architecture/test_async_db_runtime_boundaries.py -o addopts=''`
- `uv run --python 3.13.2 pytest tests/unit/domain/constants tests/unit/domain/model/test_translation_result.py tests/unit/domain/services/translation/test_text_translation_service.py tests/unit/domain/services/test_meal_translation_service.py tests/unit/domain/services/test_suggestion_translation_service.py tests/unit/infra/adapters/test_openai_translation_adapter.py tests/unit/infra/adapters/test_openai_translation_eval_fixture.py tests/unit/infra/services/ai/test_openai_translation_failures.py tests/unit/app/services/test_food_name_localizer.py tests/unit/api/test_translation_dependency_wiring.py`
- `uv run --python 3.13.2 pytest tests/integration/ai/test_openai_translation_smoke.py`
- `uv run --python 3.13.2 pytest tests/unit --cov=src --cov-fail-under=65`

## Failed Test

- `tests/architecture/test_async_db_runtime_boundaries.py::test_repository_transaction_boundary_allowlist_does_not_expand`
- Failure: allowlist mismatch
- Expected allowlist:
  - `src/infra/repositories/pgvector_meal_image_cache_repository_async.py`
- Actual offenders:
  - `src/infra/repositories/admin_meal_catalog_repository_async.py`
  - `src/infra/repositories/pgvector_meal_image_cache_repository_async.py`

### Failure Detail

The test asserts the repository transaction-boundary allowlist has not expanded. It found a new offender in `src/infra/repositories/admin_meal_catalog_repository_async.py`.

### Classification

- Pre-existing, not introduced by the current translation cutover diff.
- Reason: the file is not in `git diff --name-only HEAD` and was not modified in the current worktree snapshot.
- Implication: this is still a real architecture drift, but it is outside the translation-service change set validated here.

## Notes

- `tests/integration/ai/test_openai_translation_smoke.py` is skipped in this environment.
- The translation-focused unit slice was fully green, including the new OpenAI translation adapter, service layer, language constants, and dependency wiring.
- No build command was requested or run.

## Recommendations

1. Decide whether `src/infra/repositories/admin_meal_catalog_repository_async.py` should remain in the transaction-boundary allowlist or be refactored to avoid explicit commit/rollback calls.
2. Keep the architecture guard in CI; it is catching drift outside the translation cutover scope.
3. Add or retain translation integration coverage once the external OpenAI smoke path is enabled in CI.
