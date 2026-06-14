---
type: red-team-review
plan: food-guard-evaluation-layer
created: 2026-06-13
status: complete
---

# Red Team Review — Food Guard Plan

## Method

Manual hard-mode adversarial review. Subagent spawning not used because current multi-agent tool requires explicit user delegation outside skill text.

## Findings

| Severity | Finding | Evidence | Disposition |
|---|---|---|---|
| High | Report undercounted handlers; registered legacy URL command can bypass the guard. | `src/api/dependencies/event_bus.py` registers `AnalyzeMealImageByUrlHandler`; handler parses nutrition before `has_food`. | Accepted. Phase 3 includes legacy handler guard or explicit deletion handoff. |
| High | `bool(raw_value)` would make `"false"` true. | Python truthiness; parser currently has no `parse_is_food` method. | Accepted. Phase 2 requires strict boolean coercion tests. |
| Medium | "Early rejection" claim is misleading. | Vision call still happens before handler can read `is_food`. | Accepted. Plan wording says post-vision/pre-nutrition rejection. |
| Medium | `raw_gpt_json` success criterion is wrong for rejected scans. | Upload and scan-by-url paths save meal only after `has_food`. | Accepted. Phase 5 expects safe log/metric, not meal persistence. |
| Medium | Prompt asks for provider calories even though backend owns calories. | `Nutrition.calories` derives from macros. | Accepted. Phase 2 says do not consume provider calories; optionally tighten prompt only if low-risk. |
| Medium | Borderline food taxonomy missing. | No current docs/tests define drinks, packaged food, supplements, labels, empty plate. | Accepted. Phase 1 defines taxonomy before code. |

## Plan Changes Applied

- Phase 1 owns contract and taxonomy.
- Phase 2 owns parser/prompt tests and strict coercion.
- Phase 3 guards three registered handlers.
- Phase 4 covers API mapping and legacy route/test cleanup decision.
- Phase 5 validates no raw payload logging, no provider calorie authority, and focused test gates.

## Whole-Plan Consistency Sweep

- Searched for stale claims: "early rejection", "4 files", "two handlers", "raw_gpt_json on rejection".
- Reconciled to: post-vision guard, 3 registered handlers, no DB/schema/cache changes, rejected scans do not persist meals.
- No unresolved contradictions.
