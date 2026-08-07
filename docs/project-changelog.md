# Project Changelog

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

## 2026-08-01

### Fixed

- Catalog image generation reliability: catalog-job DB transactions are now short-lived, Cloudinary error logging and job output are sanitized, and the GitHub Actions production Cloudinary secret trio must be reconciled before the workflow is expected to run cleanly.
