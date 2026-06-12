---
title: "Service-Initiated Bandwidth Reduction"
description: "Reduce Render outbound bandwidth ~92% via image compression before Cloudinary upload, then eliminate the upload entirely with presigned direct-client upload."
status: pending
priority: P2
branch: "feature/NM-affiliate-outbox-pattern"
tags: [bandwidth, cloudinary, performance]
blockedBy: []
blocks: [260612-1128-mobile-presigned-cloudinary-upload]
created: "2026-06-12T03:52:50.706Z"
createdBy: "ck:plan"
source: skill
---

# Service-Initiated Bandwidth Reduction

## Overview

Render "Service-Initiated" (server-outbound) bandwidth is high because the server relays full-size phone images (~5MB) to Cloudinary before analysis. Gemini already receives compressed 200KB images; Cloudinary does not.

Phase 1 compresses before upload (server-only, ships today). Phase 2 eliminates the relay entirely via presigned direct-client upload (needs mobile coordination). Phase 3 removes dead code found during investigation.

Design doc: `plans/reports/brainstorm-260612-1046-service-initiated-bandwidth-reduction-report.md`

## Phases

| Phase | Name | Status | Effort |
|-------|------|--------|--------|
| 1 | [Server-Side Compression](./phase-01-server-side-compression.md) | **Skipped** | 2h |
| 2 | [Presigned Direct Upload](./phase-02-presigned-direct-upload.md) | Pending | 1d |
| 3 | [Dead Code Removal](./phase-03-dead-code-removal.md) | Pending | 2h |

**Decision:** Phase 1 skipped — jumping directly to Phase 2. Phase 2 includes the compression utility inline (needed for safe-path Gemini analysis after client uploads to Cloudinary).

## Bandwidth Projection (500 scans/day)

| After | Per-scan outbound | Daily total | Reduction |
|-------|-------------------|-------------|-----------|
| Today | ~5.2MB | ~2.6GB | baseline |
| Phase 2 (safe) | ~200KB | ~100MB | 96% |
| Phase 2 + URL Gemini | ~1KB | ~0.5MB | ~99% |

## Dependencies

Phase 2 is independent (no Phase 1 prerequisite); requires mobile app release coordination.
Phase 3 is independent.
