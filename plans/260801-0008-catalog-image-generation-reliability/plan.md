---
title: "Catalog Image Generation Reliability"
description: "Make catalog image backfills resilient to external-provider latency and safely diagnose stale Cloudinary workflow credentials."
status: completed
priority: P1
effort: "4h"
branch: "fix/catalog-image-generation"
tags: [bugfix, backend, database, infra]
blockedBy: []
blocks: []
created: "2026-07-31T17:08:22.503Z"
createdBy: "ck:plan"
source: skill
---

# Catalog Image Generation Reliability

## Overview

Repair the catalog-image GitHub Actions job without changing the working client direct-upload or admin endpoint contracts. External Cloudflare/Cloudinary work must run outside database transactions; failed uploads must not cause a stale-session commit error; the workflow must offer safe evidence for mismatched Cloudinary credentials.

## Scope

- Keep: catalog selection semantics, per-row conditional update, image prompt/model, and existing API contracts.
- Add: short-lived persistence boundaries, safe configuration error guidance, private job output, and targeted regression coverage.
- Exclude: automatic secret rotation, retry queues, changing Cloudinary upload fields, and direct-upload endpoint changes.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Transaction Boundaries](./phase-01-transaction-boundaries.md) | Completed |
| 2 | [Credential Diagnostics and Workflow Validation](./phase-02-credential-diagnostics-and-workflow-validation.md) | Completed |
| 3 | [Regression Tests and Verification](./phase-03-regression-tests-and-verification.md) | Completed |

## Dependencies

- Approved diagnosis: [catalog image generation brainstorm](../reports/260801-0000-catalog-image-generation-brainstorm.md).
- No blocking plan dependency. Operational rollout requires replacing GitHub `production` environment Cloudinary secrets as one matching account set.

## Success Criteria

- External image generation never holds an open async SQLAlchemy transaction.
- Upload failure finishes with the catalog-job failure summary, not a closed-connection commit traceback.
- Successful persistence remains conditional and race-safe.
- Workflow output contains no secret, API key, prompt, raw provider payload, or image URL.
- Direct upload and admin catalog image generation contracts remain unchanged.

## Completion Record

- Verified: 57 focused tests passed; Python compilation, Ruff, and independent code review passed.
- External rollout: replace the GitHub Actions `production` Cloudinary cloud name, API key, and API secret as one matching account set before a non-dry-run execution.
