---
phase: 3
title: "Dead Code Removal"
status: pending
priority: P3
effort: "2h"
dependencies: []
---

# Phase 3: Dead Code Removal

## Overview

Remove code identified during bandwidth investigation that is never executed in production. No behavior change — purely cleanup. Can run after Phase 1; does not depend on Phase 2.

## Context Links

- Design doc: `plans/reports/brainstorm-260612-1046-service-initiated-bandwidth-reduction-report.md`
- Dead event handler: `src/app/handlers/event_handlers/meal_analysis_event_handler.py`
- Event never published: grep for `MealImageUploadedEvent(` returns only the class definition
- Unused adapters: `cloudflare_image_generator.py`, `imagen_image_generator.py`, `pollinations_image_generator.py`, `unsplash_image_adapter.py`

## Dead Code Inventory

| File | Reason dead |
|------|-------------|
| `src/app/handlers/event_handlers/meal_analysis_event_handler.py` | `MealImageUploadedEvent` never published — event handler never fires |
| `src/app/events/meal/meal_image_uploaded_event.py` | Event class with no publisher |
| `src/infra/adapters/cloudinary_image_store.py` — `load()` + `load_async()` | Only called by dead event handler |
| `src/infra/adapters/cloudflare_image_generator.py` | Class defined, never imported or instantiated in handlers |
| `src/infra/adapters/imagen_image_generator.py` | Same |
| `src/infra/adapters/pollinations_image_generator.py` | Same |
| `src/infra/adapters/unsplash_image_adapter.py` | Same |
| `src/api/dependencies/event_bus.py` — `MealImageUploadedEvent` subscription | Line 629 subscribes handler that never fires |

**Note on `analyze_by_url_with_strategy`:** This method is broken (passes URL text as fake image bytes) but is repaired in Phase 2, not removed here. Skip it in this phase.

## Related Code Files

- **Delete:** `src/app/handlers/event_handlers/meal_analysis_event_handler.py`
- **Delete:** `src/app/events/meal/meal_image_uploaded_event.py`
- **Delete:** `src/infra/adapters/cloudflare_image_generator.py`
- **Delete:** `src/infra/adapters/imagen_image_generator.py`
- **Delete:** `src/infra/adapters/pollinations_image_generator.py`
- **Delete:** `src/infra/adapters/unsplash_image_adapter.py`
- **Modify:** `src/infra/adapters/cloudinary_image_store.py` — remove `load()` + `load_async()`
- **Modify:** `src/api/dependencies/event_bus.py` — remove event subscription + imports
- **Modify:** `src/app/events/meal/__init__.py` — remove `MealImageUploadedEvent` export
- **Modify:** `src/app/events/__init__.py` — remove `MealImageUploadedEvent` export

## Implementation Steps

### Step 1 — Verify `MealImageUploadedEvent` is never published

```bash
grep -rn "MealImageUploadedEvent(" src/ --include="*.py" | grep -v "class MealImageUploadedEvent"
```

Expected: no output. If any publisher is found, STOP and investigate before deleting.

### Step 2 — Verify image generators are never used

```bash
grep -rn "CloudflareImageGenerator\|PollinationsImageGenerator\|ImagenImageGenerator\|UnsplashImageAdapter" \
  src/ --include="*.py" | grep -v "^src/infra/adapters/"
```

Expected: no output (imports only within their own files). If used anywhere else, STOP.

### Step 3 — Verify `load_async` / `load` callers

```bash
grep -rn "load_async\|\.load(" src/ --include="*.py" | grep -v "__pycache__" | grep -v "cloudinary_image_store"
```

Expected: only `meal_analysis_event_handler.py` (the dead handler). If called from anywhere else, remove only the event handler, not the methods.

### Step 4 — Remove event handler and event class

```bash
git rm src/app/handlers/event_handlers/meal_analysis_event_handler.py
git rm src/app/events/meal/meal_image_uploaded_event.py
```

Remove the subscription from `src/api/dependencies/event_bus.py`:

Find and delete these lines (around line 629):
```python
# Remove this import
from src.app.events.meal import MealImageUploadedEvent

# Remove this subscription
event_bus.subscribe(MealImageUploadedEvent, meal_analysis_handler.handle)
```

Also remove the `MealAnalysisEventHandler` import and instantiation from `event_bus.py`.

### Step 5 — Remove `MealImageUploadedEvent` from `__init__.py` exports

In `src/app/events/meal/__init__.py`, remove:
```python
from src.app.events.meal.meal_image_uploaded_event import MealImageUploadedEvent
```
and remove `"MealImageUploadedEvent"` from `__all__` if present.

In `src/app/events/__init__.py`, same cleanup.

### Step 6 — Remove `load()` and `load_async()` from CloudinaryImageStore

In `src/infra/adapters/cloudinary_image_store.py`, delete:
- `def load(self, image_id: str) -> bytes | None:` and its body
- `async def load_async(self, image_id: str) -> bytes | None:` and its body

Also remove `get_url_async()` if it's only used by `load_async` — verify:
```bash
grep -rn "get_url_async" src/ --include="*.py"
```

Remove `get_url()` only if it has no other callers beyond `load()`:
```bash
grep -rn "get_url\b" src/ --include="*.py" | grep -v "cloudinary_image_store\|test_"
```

`meals.py:163` uses `image_store.get_url()` as fallback — keep `get_url()` and `get_url_async()`.

### Step 7 — Delete unused adapter files

```bash
git rm src/infra/adapters/cloudflare_image_generator.py \
       src/infra/adapters/imagen_image_generator.py \
       src/infra/adapters/pollinations_image_generator.py \
       src/infra/adapters/unsplash_image_adapter.py
```

### Step 8 — Remove any __init__.py exports of deleted adapters

```bash
grep -rn "cloudflare_image\|imagen_image\|pollinations\|unsplash" \
  src/ --include="*.py" | grep -v "__pycache__"
```

Delete any found import lines.

### Step 9 — Run full test suite

```bash
pytest tests/ -x -q 2>&1 | tail -20
```

Expected: all pass. If any test imports the deleted modules, delete or update those tests too.

### Step 10 — Commit

```bash
git commit -m "refactor: remove dead event handler, unused image adapters, and unreachable load path"
```

## Success Criteria

- [ ] `MealImageUploadedEvent` has no publisher (grep confirms) before deletion
- [ ] `meal_analysis_event_handler.py` deleted
- [ ] `meal_image_uploaded_event.py` deleted
- [ ] `load()` and `load_async()` removed from `CloudinaryImageStore`
- [ ] `get_url()` and `get_url_async()` retained (still used by meals.py fallback)
- [ ] All 4 unused adapter files deleted
- [ ] `event_bus.py` subscription removed; no import errors
- [ ] Full test suite passes

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| A future feature needs `load_async` | It's trivial to re-add; the logic is just `httpx.get(get_url(id))` |
| Deleted adapter still referenced in a test | Step 9 catches it; delete the test if it only tested the now-removed adapter |
| Event published from a background job outside the main app | Step 1 grep must confirm before deleting |
