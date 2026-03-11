# Tester Agent Memory

## Test Infrastructure (Backend)
- **Test runner**: `python3 run_tests.py [command]` in backend/ directory
- **Framework**: pytest (requires installation, not auto-available in environment)
- **Test files**: 88 total, all compile successfully, no syntax errors
- **Config**: `pytest.ini` at backend root with markers: unit, integration, api, validation, performance
- **Coverage**: pyproject.toml includes coverage config, omits migrations, infra services, tests
- **Key script**: `run_tests.py` provides health, fast, unit, integration, api, validation, coverage commands

## Nutrition Accuracy Implementation (2026-03-11)
**Status**: Code-complete, backward compatible, needs test coverage for new modules

### Core Changes Verified
1. **Macros model** (`src/domain/model/nutrition/macros.py`)
   - Added fiber/sugar fields with defaults (0.0)
   - New formula: `P*4 + (C-fiber)*4 + fiber*2 + F*9` instead of `P*4 + C*4 + F*9`
   - Backward compatible when fiber=0 (yields identical results)
   - Validation: rejects negatives, enforces max 5000g per field

2. **DB models** updated for fiber/sugar storage
   - `food_item.py`: fiber, sugar columns (Float, default=0)
   - `nutrition.py`: fiber, sugar columns (Float, default=0)
   - Conversions: `to_domain()` and `from_domain()` include fiber/sugar

3. **New modules** (need test coverage)
   - `src/domain/constants/food_density.py`: 30+ foods with density map, `get_density()` lookup
   - `src/domain/services/meal_suggestion/macro_validation_service.py`: Post-generation validation (⚠️ still uses old formula P*4+C*4+F*9, needs update)

4. **Enhanced services**
   - `nutrition_calculation_service.py`: Density-aware ml→g conversion, fiber/sugar propagation
   - Prompt templates updated for fiber extraction
   - API schemas updated with fiber_g/sugar_g fields

### Critical Issues
1. **P1 - Formula mismatch**: `macro_validation_service.py:30` uses old formula, needs fiber adjustment
2. **P2 - No tests**: `food_density.py` and `macro_validation_service.py` have 0% test coverage
3. **P4 - Dependencies**: pytest/langchain_core not installed in test environment

### Backward Compatibility
- All 88 existing test files compile
- Expected test results unchanged (calorie calculations identical when fiber=0)
- No breaking DB changes (columns added with defaults)

## Test Execution Gotchas
- **Environment**: Python 3.14.0 (supports project), pytest not auto-installed
- **Solution**: Run `python3 run_tests.py unit` which handles pytest invocation internally
- **Dependencies**: requirements.txt + requirements-test.txt needed before running
- **langchain_core**: Missing but not required for syntax validation, only for import testing

## Files to Monitor
- `src/domain/services/meal_suggestion/macro_validation_service.py` - needs formula fix
- `tests/unit/domain/test_nutrition_validation.py` - verify existing tests pass
- Migration files in `src/infra/database/migrations/` - verify fiber/sugar columns exist in migrations

## Next Test Run Command
```bash
cd /Users/tonytran/Projects/nutree-universe/backend
python3 run_tests.py unit --verbose  # Run all unit tests
python3 run_tests.py coverage        # Generate coverage report
```
