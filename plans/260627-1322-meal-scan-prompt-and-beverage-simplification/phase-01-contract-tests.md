# Phase 01 Contract Tests

## Context Links

- Brainstorm: `plans/reports/brainstorm-260627-1322-meal-scan-prompt-and-beverage-simplification-report.md`
- Upload handler: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Scan-by-url handler: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Current tests: `tests/unit/handlers/command_handlers/test_beverage_scan_routing.py`
- Current tests: `tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py`

## Overview

Priority: high.
Status: completed.

First lock the approved behavior before changing implementation.

## Requirements

- Caloric packaged beverage output follows standard meal creation path.
- No hydration entry is created by upload or scan-by-url meal scan.
- Existing non-food guard still rejects before meal persistence.
- Water or zero-cal beverage does not create a hydration entry from meal scan.

## Architecture

Tests should exercise command handlers with mocked vision output. Do not hit
real providers.

## Related Code Files

- Modify: `tests/unit/handlers/command_handlers/test_beverage_scan_routing.py`
- Modify: `tests/unit/handlers/command_handlers/test_scan_by_url_beverage_routing.py`
- Read: `tests/unit/handlers/command_handlers/test_food_guard_command_handlers.py`

## Implementation Steps

1. Replace hydration-only beverage expectations with standard meal expectations.
2. Assert `uow.hydration_entries.add` is not called.
3. Assert meal source stays `scanner`.
4. Add zero-cal drink case that fails normal meal validation without hydration write.
5. Run focused tests and confirm they fail before implementation.

## Todo List

- [x] Update upload beverage routing tests.
- [x] Update scan-by-url beverage routing tests.
- [x] Add no-hydration-write assertions.
- [x] Add zero-cal drink boundary case.

## Success Criteria

- Focused tests express the new contract.
- Tests fail against current beverage branch before implementation.

## Risk Assessment

- Existing mocks may assume beverage path avoids parser calls. Update mocks to
  reflect normal parser path.

## Security Considerations

- Keep test payloads synthetic. Do not include real user images or raw provider
  outputs.

## Next Steps

Proceed to prompt contract cleanup.
