---
phase: 1
title: "Transaction Boundaries"
status: completed
priority: P1
effort: "1.5h"
dependencies: []
---

# Phase 1: Transaction Boundaries

## Overview

Separate catalog reads and per-image writes from Cloudflare/Cloudinary calls, avoiding an idle Neon transaction during remote I/O.

## Requirements

- Functional: select target meal projections before generation; generate with no active UoW; use a fresh UoW for each conditional update and commit.
- Functional: a provider exception increments `failed`, continues to the next meal, and returns a summary without an exit-time commit attempt.
- Non-functional: retain bounded memory and current update race protection; no public contract change.

## Architecture

`select targets (short UoW) -> close DB session -> generate externally -> conditional update + commit (fresh short UoW per success)`. The existing `image_url IS NULL OR trim(image_url) = ''` predicate remains the concurrency fence.

## Related Code Files

- Modify: `scripts/generate_catalog_meal_images.py` — transaction scoping and result flow.
- Modify: `tests/unit/scripts/test_generate_catalog_meal_images.py` — script lifecycle tests.

## Implementation Steps

1. Extract lightweight target data needed for prompt construction before closing the read UoW.
2. Iterate external generation after the read UoW exits.
3. Persist each successful URL through a dedicated helper that opens, conditionally updates, commits, and closes its own UoW.
4. Treat a lost conditional update as `skipped`; do not retry or overwrite an image created concurrently.
5. Ensure all error paths roll back/close their fresh session and preserve accurate selected/updated/skipped/failed counts.
6. Replace raw prompt and generated URL output with safe catalog identity and outcome fields.

## Success Criteria

- [x] No UoW spans `generator.generate_url`.
- [x] Cloudinary failure cannot trigger the prior exit-time `Transaction.commit()` error.
- [x] Existing per-row conditional persistence behavior remains intact.

## Risk Assessment

- Detached ORM relationships may lazy-load after the read UoW closes. Mitigate by retaining eager loading or converting to a prompt-ready projection before exit.
- A duplicate generation can occur if another worker writes first. The conditional update intentionally prevents overwrite; the generated remote asset is an acceptable orphan under current behavior.
