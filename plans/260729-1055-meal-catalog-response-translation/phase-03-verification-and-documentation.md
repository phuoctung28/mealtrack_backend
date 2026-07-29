---
phase: 3
title: Verification and documentation
status: completed
priority: P2
effort: 3h
dependencies:
  - 2
---

# Phase 3: Verification and documentation

## Overview

Prove localized response behavior, graceful degradation, and compatibility with existing catalog recommendation behavior. Update API documentation only after focused verification passes.

## Test Scenario Matrix

| Scenario | Expected result |
|---|---|
| `en` / no header | Canonical English; translator not called |
| Supported non-English | Allowlisted text translated in summary/detail/mutation shapes |
| Unsupported language | Middleware resolves `en`; canonical response |
| Missing key | Endpoint succeeds with English |
| Provider exception/short batch | Safe canonical fallback |
| Repeated text | One request-level translation per unique text |
| Persisted plan | Same stored selection/ranking/state, localized only at projection |

## Related Code Files

- Modify: `docs/api-endpoints.md` — document request-language behavior and fallback.
- Modify tests adjacent to the recommendation route and middleware seams.

## Implementation Steps

1. Run focused localizer, middleware, response-schema, and all recommendation route tests.
2. Run `ruff check` on changed source/tests and applicable `mypy` checks.
3. Run the broader recommendation/API subset; do not claim live DeepL verification unless executed.
4. Inspect the final diff for controlled-field translation, raw provider logging, schema drift, or catalog persistence changes.

## Success Criteria

- [x] English, all supported non-English, missing-key, failure, and nested alternative paths pass.
- [x] Ranking/persistence tests remain green.
- [x] Ruff and applicable mypy checks pass.
- [x] API docs state `Accept-Language` behavior and English fallback.
- [x] No migration or canonical catalog data changes.

## Security and Performance

- DeepL calls remain off the request path for English.
- Translation failures cannot expose provider payloads or request content in logs.
- Deduplication and bounded response traversal prevent unbounded provider requests.
