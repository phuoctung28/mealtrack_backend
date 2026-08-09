# Project Changelog

## 2026-08-01

### Fixed

- Catalog image generation reliability: catalog-job DB transactions are now short-lived, Cloudinary error logging and job output are sanitized, and the GitHub Actions production Cloudinary secret trio must be reconciled before the workflow is expected to run cleanly.
