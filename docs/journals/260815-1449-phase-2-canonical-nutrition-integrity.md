---
date: 2026-08-15 14:49
severity: medium
component: canonical nutrition integrity
status: resolved
origin_delivery_sha: 5415897c55173f446229441afbc0a79ed80c3f2f
---

# Phase 2 Canonical Nutrition Integrity

## Context

Phase 2 finished the canonical nutrition integrity pass. The work stayed centered on the shared `nutrition_integrity_v1` path so the backend keeps one source of truth instead of scattered ad hoc corrections.

## What Happened

We completed the canonical handling for servings labeled `100g` with `g=1` as the normalized provider-facing unit. That closes the mismatch between provider labels and internal canonical mass handling, which had been leaking ambiguity into downstream nutrition calculations.

## Decisions

We kept the fix inside the shared `nutrition_integrity_v1` flow instead of branching logic per caller. That was the right call: less duplication, fewer drift points, and one place to reason about normalization. The implementation was validated by a focused 162-test pass, but only in the offline synthetic harness. That is useful evidence, not deployment proof.

## Impact / Verification

The targeted 162 pass result confirmed the canonical path behaves as intended for the covered cases. The important limitation is that the validation was synthetic and offline, so it does not prove live provider or production behavior. Also, an unrelated cron full-unit failure showed up in the broader test surface; it was not caused by this nutrition work, but it is still a real signal that the full suite is not clean.

## Next

Keep the canonical nutrition integrity path as the shared implementation point, and treat live verification as a separate step. The right follow-up is to resolve the unrelated cron failure, then validate this path again against a non-synthetic provider-backed run before anyone talks about production readiness.
