---
phase: 2
title: "Graph Runtime And Acquisition Nodes"
status: complete
priority: P1
effort: "1d"
dependencies: [1]
---

# Phase 2: Graph Runtime And Acquisition Nodes

## Overview

Introduce a runtime-bound graph runner so nodes can do real work without
placing large/sensitive payloads in graph state. Move image acquisition and scan
mode selection into graph nodes.

## Context Links

- Workflow seam: `src/app/services/meal_analyze_workflow.py`
- Graph package: `src/app/graphs/meal_analyze/`
- Upload command: `src/app/commands/meal/upload_meal_image_immediately_command.py`
- Scan command: `src/app/commands/meal/scan_by_url_command.py`
- Image compression: `src/domain/utils/image_compression.py`

## Requirements

- Functional: direct upload graph path saves image and records safe image
  metadata.
- Functional: scan-by-url graph path downloads Cloudinary bytes and compresses
  non-label images.
- Functional: food-label path supports optional crop download.
- Non-functional: no raw Cloudinary URL or bytes in graph state.

## Architecture

Create a runtime object bound per invocation:

```python
@dataclass
class MealAnalyzeRuntime:
    command: UploadMealImageImmediatelyCommand | ScanByUrlCommand
    image_store: ImageStorePort | None
    download_image_bytes: Callable[..., Awaitable[bytes]] | None
    compress_image: Callable[[bytes], bytes]
```

Graph nodes close over runtime or receive it through a runner. State stores only
`scan_mode`, `user_id`, `target_date`, `image_id`, `content_kind`, and node
outputs that are safe to inspect.

## Related Code Files

- Create: `src/app/graphs/meal_analyze/runtime.py`
- Modify: `src/app/graphs/meal_analyze/state.py`
- Modify: `src/app/graphs/meal_analyze/nodes.py`
- Modify: `src/app/graphs/meal_analyze/graph.py`
- Modify: `src/app/services/meal_analyze_workflow.py`
- Modify: upload and scan-by-url handler constructors only as needed.

## Tests Before

1. Node tests for upload acquisition with image store mock.
2. Node tests for URL scan acquisition with downloader/compressor mocks.
3. Food-label crop selection test.
4. State-safety test proving URLs/bytes are not returned.

## Refactor

Move these responsibilities out of legacy handler bodies for graph-enabled path:

- Upload image to Cloudinary for direct uploads.
- Download image bytes for scan-by-url.
- Compress regular scan-by-url bytes.
- Choose full image vs crop image for food-label.

Keep legacy methods intact for graph-disabled path until Phase 3 completes.

## Tests After

- New node tests pass.
- Existing upload/scan tests still pass with graph disabled.

## Implementation Steps

1. Add `MealAnalyzeRuntime` and safe state fields.
2. Build graph with runtime-bound node callables.
3. Implement `acquire_image` node.
4. Implement `select_analysis_mode` conditional edge.
5. Update workflow to call graph runner for acquisition.

## Success Criteria

- [x] Graph-enabled path does image acquisition inside graph nodes.
- [x] Raw URL/bytes excluded from returned graph state.
- [x] Graph-disabled legacy path unchanged.

## Risk Assessment

- Risk: moving image upload changes failure timing.
- Mitigation: keep same exception classes/messages at API boundary; assert route
  behavior in focused tests.
