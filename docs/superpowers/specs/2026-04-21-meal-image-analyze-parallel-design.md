# Meal Image Analyze Latency Design (Parallel AI + Upload)

## Problem

`POST /v1/meals/image/analyze` is too slow for interactive use because it performs image upload and AI analysis in the same synchronous chain. Current logs show AI phase around 6.5s while end-to-end request time is ~12.6s.

Goal: reduce p50/p95 latency by overlapping independent work without reducing AI confidence.

## Constraints and Decisions

1. Keep immediate processing on backend (no mandatory client direct upload flow).
2. Preserve analysis confidence by running AI on original uploaded bytes.
3. Image is required for a successful meal: if image upload fails, request must fail.
4. Keep existing endpoint contract and error shape compatible with current clients.

## Recommended Approach

Run AI analysis and image upload concurrently inside `UploadMealImageImmediatelyHandler`, then finalize response only after both complete.

- Start two tasks after request validation:
  - Task A: `vision_service.analyze(...)` on original `file_contents`.
  - Task B: `image_store.save(...)` for persistence.
- Await both and evaluate outcomes through a deterministic failure matrix.
- Persist meal as `READY` only when both AI and upload succeed.
- If AI succeeds but upload fails: set meal status to `FAILED`, return validation-style failure.
- If AI fails/non-food but upload succeeds: optionally delete uploaded image best-effort, return existing non-food error.

This removes serialized waiting between upload and AI while preserving quality and image-required semantics.

## Detailed Flow

1. Route performs current validations and builds command.
2. Handler creates initial meal (`ANALYZING`) as today.
3. Handler launches parallel operations:
   - `upload_task`: Cloudinary save.
   - `analysis_task`: vision analysis + parsing.
4. Handler awaits completion of both tasks.
5. Apply failure matrix:
   - **Both success** → populate nutrition/dish/image URL; save `READY`; return detailed response.
   - **Analysis fail + upload success** → perform best-effort image cleanup; save `FAILED`; map to current `NOT_FOOD_IMAGE` behavior where applicable.
   - **Analysis success + upload fail** → save `FAILED`; return upload failure (non-2xx).
   - **Both fail** → save `FAILED`; prioritize analysis-domain error mapping if non-food, else generic failure.
6. Publish cache invalidation event only on successful final persistence (existing behavior target).

## Error Handling Rules

- Do not silently downgrade to image-less READY meals.
- Maintain explicit logs for each branch:
  - `[PHASE-UPLOAD-START|COMPLETE|FAIL]`
  - `[PHASE-ANALYSIS-START|COMPLETE|FAIL]`
  - `[ANALYSIS-COMPLETE]` with per-phase elapsed and total elapsed.
- Preserve existing API error mapping contracts in route layer.

## Rollout Plan

Introduce a feature flag to gate parallel mode:

- `MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED` (default false).
- Canary enable for a subset of users/traffic.
- Monitor:
  - endpoint p50/p95 latency
  - upload failure rate
  - non-food rejection rate
  - overall 5xx/4xx shifts

Full rollout after latency and error rates are stable.

## Testing Strategy

1. Unit tests for handler parallel branch:
   - both success
   - analysis fail/upload success
   - analysis success/upload fail
   - both fail
2. Assert final meal status transitions and saved fields in each branch.
3. Assert route-level error mapping remains compatible.
4. Integration test path for `/v1/meals/image/analyze` with mocked upload/AI timing to confirm no serialized dependency.

## Out of Scope

- Replacing endpoint with required client direct-upload flow.
- Changing nutrition/translation business rules.
- UI-level changes beyond existing contract compatibility.
