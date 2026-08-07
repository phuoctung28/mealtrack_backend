# CodeQL Barcode Logging Redaction

## Summary

- Removed tainted provider/result fields from barcode lookup log arguments flagged by CodeQL.
- Kept operational barcode lookup signals limited to controlled source labels, elapsed time, booleans, and exception class names.
- Preserved explicit empty USDA FDC API keys in tests so local environment variables do not override the missing-key path.

## Verification

- `.venv/bin/ruff check src/app/handlers/query_handlers/lookup_barcode_query_handler.py src/infra/adapters/food_data_service.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_logging.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/infra/adapters/test_food_data_service.py`
- `.venv/bin/pytest tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_async.py tests/unit/handlers/query_handlers/test_lookup_barcode_query_handler_logging.py tests/unit/infra/adapters/test_food_data_service.py -q`
- `.venv/bin/lint-imports`
- `.venv/bin/pytest tests/unit/architecture/test_logging_ownership_guardrails.py -q`
- `.venv/bin/pytest tests/unit --ignore=tests/integration -m "not integration" --cov=src --cov-report=term-missing --cov-fail-under=65 -q`
