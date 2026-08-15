# Parse-Text Plan Red-Team Adjudication

Date: 2026-08-14

Reviewed:

- `260814-1048-red-team-security-parse-text-plan.md`
- `260814-1048-red-team-assumptions-parse-text-plan.md`
- `260814-1048-red-team-failure-modes-parse-text-plan.md`

## Findings

| ID | Finding | Severity | Disposition | Applied to |
|---|---|---:|---|---|
| S1 | Guest limiter trusts unsigned JWT subject | Critical | Reject | Pre-existing cross-cutting limiter issue; request-wide caps reduce this feature's worst-case cost. Track separately; do not redesign auth in nutrition plan. |
| S2 | `current_items` bypasses prompt sanitation | High | Accept | Phases 1-2 bounded refinement validation and injection tests. |
| S3 | Refinement JSON is unbounded | High | Accept | Phase 2 item/string/nesting/12 KiB limits before provider work. |
| S4 | No aggregate request call budget | High | Accept | Phases 1-2 define 2 AI, 5 search, 5 detail, concurrency 3, 3-second deadline. |
| S5 | Transitive dependencies log raw data | High | Accept | Phase 2 includes sanitizer/FatSecret log canaries and remediation. |
| S6 | Live guard trusts CLI environment label | High | Accept | Phase 3 requires authoritative staging plus enable and confirmation gates. |
| S7 | Live mode has no spend/clock kill switch | High | Accept | Phase 3 caps cases, calls, concurrency, and wall time. |
| S8 | Report path is not guaranteed ignored | Medium | Accept | Phase 3 defaults to OS temp; verifies ignored paths, 0600, no overwrite. |
| S9 | Serving metadata is unbounded | Medium | Accept | Phase 2 caps/counts/sanitizes accepted unit metadata. |
| A1 | Normalization erases preparation | High | Accept | Phase 2 matches original row preparation or bypasses local lookup. |
| A2 | Draft validator conflicts with 110 g contract | High | Accept | Phase 2 reuses existing 110 g invariant and removes fiber/sugar inequalities. |
| A3 | FatSecret detail lacks fiber/sugar | High | Accept | Phase 2 defines required P/C/F/energy/basis and optional fiber/sugar mapping. |
| A4 | Fiber/sugar disappear through app DTO | Critical | Accept | Phases 1-2 add internal DTO propagation and route-calorie tests without new public fields. |
| A5 | Local source could widen API values | High | Accept | Phase 2 allowlists origin-to-existing-public-source mapping; unknown origins bypass. |
| A6 | Schema and semantic retries can stack | High | Accept | Phases 1-2 define one two-generation state machine. |
| A7 | Per-item timeout multiplies to 20 items | High | Accept | Phases 1-3 use one request deadline, call caps, concurrency, cancellation tests. |
| A8 | Caller inventory was incomplete | Medium | Accept | Phase 2 records first production resolver consumer, 1+6 handler constructors, and shared provider consumers. |
| A9 | Handler harness cannot prove HTTP contract | High | Accept | Phase 3 separates semantic evaluation from authenticated/guest route gates. |
| F1 | Request deadline unowned across fan-out | High | Accept | Same request-level budget/cancellation changes as A7. |
| F2 | Resolver reuse hides a new production seam | High | Accept | Phase 2 labels first production consumer and adds rollback flag. |
| F3 | Shared `search_foods()` blast radius | High | Accept | Phase 2 forbids semantic changes and uses staged methods only. |
| F4 | Validator assumes unavailable detail fields | High | Accept | Same explicit mapped-detail contract as A3. |
| F5 | Semantic retry unit undefined | High | Accept | Retry is whole-request only, never per item, under shared call ceiling. |
| F6 | Phase 1 asserts a future staged seam | Medium | Accept | Phase 1 uses a composite fake and an observable expected-red call assertion. |
| F7 | No rollback at shared composition root | Medium | Accept | Phase 2 adds default-off structured-resolution flag and legacy-path test. |
| F8 | Harness may use different timeouts | Medium | Accept | Phase 3 uses the handler's timeout config in deterministic slow-provider gates. |

## Sticky Decisions Preserved

- Parse-text only; authenticated and guest share the work.
- Public response field names and routes remain backward compatible.
- No vector RAG, DB migration, mobile work, image-scan work, or provider change.
- Backend derives all calories from the final macro set.

## Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all three phase files.
- Decision deltas checked: 11.
- Reconciled stale references: 11.
- Unresolved contradictions: 0.

## Separate Follow-Up

The unsigned-JWT guest limiter finding is real but predates and exceeds this
nutrition scope. It should receive a dedicated security investigation. This
plan does not worsen maximum AI attempts and replaces potentially 20 enriched
searches (each fetching multiple details) with strict request-level call caps.
