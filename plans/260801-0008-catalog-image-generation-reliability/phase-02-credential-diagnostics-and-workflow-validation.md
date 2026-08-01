---
phase: 2
title: "Credential Diagnostics and Workflow Validation"
status: completed
priority: P1
effort: "1h"
dependencies: [1]
---

# Phase 2: Credential Diagnostics and Workflow Validation

## Overview

Provide safe failure context and validate the workflow configuration boundary without disclosing Cloudinary credentials.

## Requirements

- Functional: distinguish configuration validation failures from provider upload failures in job output using fixed safe messages only.
- Functional: document/check that GitHub Actions uses a matching cloud name, API key, and API secret in the `production` environment.
- Non-functional: never log secrets, API keys, URLs, prompts, image bytes, or raw Cloudflare responses.

## Related Code Files

- Modify: `.github/workflows/generate-catalog-meal-images.yml` — safe preflight checks and operational guidance.
- Read: `src/infra/adapters/cloudinary_image_store.py` — preserve its upload and direct-upload signature contracts unchanged.

## Implementation Steps

1. Preserve non-empty secret validation and add no key/secret fingerprints or hashes.
2. Add a failure message that names the expected corrective action: replace the three `production` Cloudinary secrets as a matching account set.
3. Do not change the upload parameters or signature algorithm; Cloudinary SDK signing is correct for the logged request string.
4. Keep the direct-upload token endpoint and Cloudinary adapter public methods backward compatible.

## Success Criteria

- [x] Workflow errors direct operators to reconcile the three Cloudinary secrets without printing their values.
- [x] A signature failure retains enough safe context to distinguish it from Cloudflare generation and DB persistence failures.
- [x] Existing upload-token response remains unchanged.

## Security Considerations

Credential values must not enter logs, hashes, fingerprints, or output. Prefer presence-only validation plus fixed remediation guidance.
