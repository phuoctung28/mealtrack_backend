# Project Changelog

**Status:** Stateful release notes — archived; not evergreen product authority  
**Evergreen route:** see `docs/codebase-summary.md` and root `README.md`

## 2026-08-18

### Fixed

- Versioned meal ingredient adds now allow client-generated item IDs; ownership
  validation remains restricted to updates and removals.

## 2026-08-07

### Changed

- Profile and TDEE age floor is **12** (App Store alignment); web-funnel birthdate
  validation remains its own lead contract until that path is aligned.
- Meal edit now supports independent meal- and ingredient-level nutrition
  overrides: absolute calories/macros while set, with clear/restore back to
  source nutrition.
- Documentation refresh: evergreen docs no longer hand-maintain inventory
  counts; web-funnel auth path and nutrition-override contracts are documented.

## 2026-08-04

### Changed

- Updated the active web purchase handoff to resume through normal Firebase
  passwordless email-link sign-in, while retaining RevenueCat verification and
  idempotent backend finalization.
- Replaced the temporary Google/Apple-only activation surface with normal
  Firebase passwordless email-link sign-in followed by silent RevenueCat
  redemption, hash-only preflight, provider-verified finalization, idempotent
  retries, and direct Home routing.
- Removed the dedicated Flutter activation screen while retaining the
  client-side RevenueCat customer-ID mapping replacement: authenticated users
  use their Firebase UID consistently.
- Kept legacy backend claim endpoints disabled by default for migration safety.
- Redemption preflight and provider-alias correlation close anonymous web
  checkout to authenticated Firebase UID attachment.

## 2026-08-01

### Fixed

- Catalog image generation reliability: catalog-job DB transactions are now short-lived, Cloudinary error logging and job output are sanitized, and the GitHub Actions production Cloudinary secret trio must be reconciled before the workflow is expected to run cleanly.
