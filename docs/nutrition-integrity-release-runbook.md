# Nutrition Integrity Release Runbook

This runbook covers the Phase 6 backend gate. It is evidence collection and
does not authorize production data mutation.

## Before activation

- Confirm `origin/delivery` contains the required delivery merge SHA and record
  the deployed backend revision separately from the source branch.
- The migration-created control row is intentionally pending while
  `activation_run_id` is NULL. During this window, verified legacy references
  remain readable so the additive migration cannot cause a catalog outage.
- Apply the additive migration with bounded `lock_timeout` and
  `statement_timeout`; capture migration output and `EXPLAIN` evidence for the
  public eligibility query.
- Run `python scripts/nutrition_integrity.py audit` against a read-only target.
  Record only aggregate counts, active policy, and generation. Do not copy
  nutrition payloads, query text, provider IDs, credentials, or database URLs.
- Produce a versioned manifest of IDs and digests. Keep the manifest outside
  the repository and require an operator approval reference for every apply.
- Reclassify the complete verified cohort in bounded, reviewed batches. Set
  valid rows to the active policy version and quarantine reviewed invalid rows;
  preserve the editorial `is_verified` decision and append transition events.
- Call the atomic policy activation only after the cohort is complete. It sets
  `activation_run_id`, advances the generation, and switches public reads to
  materialized eligibility. Never set the activation marker by hand.

## Transition and cache gate

- Quarantine and restore with `scripts/nutrition_integrity.py` are dry-run by
  default. `--apply` requires the current digest and review reference; a stale
  digest must abort without changing the row.
- Verify every committed state transition increments
  `catalog_integrity_generation` in the same transaction and appends one
  ledger event. Confirm Redis keys use the active policy and generation.
- Warm-cache evidence must show quarantine hides the reference and a forward
  restore makes it visible only after the new generation is read.

## Rollback and release

- Rollback application code only after checking the active DB policy is
  supported by the deployed revision. Never downgrade a non-empty integrity
  ledger.
- A policy activation requires a complete classified cohort and an atomic
  control-row update. If parity, cache, CI, staging, device, or read-only Neon
  evidence is missing, stop the release.
- Keep legacy removal as a separate approval. The attempts, completeness,
  active-device, release-age, and zero-regression gates must be recorded for
  the required observation window before any sunset change.
