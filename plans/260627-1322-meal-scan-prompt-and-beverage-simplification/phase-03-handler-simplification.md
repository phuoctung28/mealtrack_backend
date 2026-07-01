# Phase 03 Handler Simplification

## Context Links

- Upload handler: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Scan-by-url handler: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Beverage helper: search for `_handle_beverage_scan`
- Beverage domain params: search for `build_beverage_scan_params`

## Overview

Priority: high.
Status: completed.

Remove special packaged-beverage routing from meal scan endpoints.

## Requirements

- Upload meal scan never diverts to hydration based on `beverage_metadata`.
- Scan-by-url never diverts to hydration based on `beverage_metadata`.
- Normal meal parser path handles drinks as food items.
- Existing non-food and empty nutrition guards remain.

## Architecture

Keep API route shape unchanged. This is a handler behavior simplification, not
a new endpoint or schema surface.

## Related Code Files

- Modify: `src/app/handlers/command_handlers/upload_meal_image_immediately_command_handler.py`
- Modify: `src/app/handlers/command_handlers/scan_by_url_command_handler.py`
- Possibly remove unused imports from both files.
- Read: `src/domain/services/beverage_scan_service.py` or equivalent helper module.

## Implementation Steps

1. Remove upload handler branch that calls `_handle_beverage_scan`.
2. Remove or dead-code-clean `_handle_beverage_scan` if no other caller remains.
3. Remove scan-by-url beverage branch.
4. Clean unused hydration imports only where safe.
5. Run focused command-handler tests.

## Todo List

- [x] Remove upload beverage branch.
- [x] Remove scan-by-url beverage branch.
- [x] Clean unused imports/helpers.
- [x] Verify normal meal persistence for caloric beverages.

## Success Criteria

- Handler tests pass.
- No meal scan path calls `uow.hydration_entries.add`.
- Meal cache invalidation is used for scan-created drinks.

## Risk Assessment

- Removing helper code may affect delete/detail compatibility for existing
  hydration-only beverage scan rows. Do not remove compatibility reads unless
  tests prove they are unused or obsolete.

## Security Considerations

- No new data is stored beyond normal meal scan data.

## Next Steps

Update docs and run verification gates.
