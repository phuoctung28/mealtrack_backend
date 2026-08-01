---
title: "Catalog Image Generation Failure Diagnosis"
status: approved
created: 2026-08-01
branch: fix/catalog-image-generation
tags: [bugfix, backend, cloudinary, database]
---

# Catalog Image Generation Failure Diagnosis

## Summary

The catalog-image workflow has two separate failures. The Cloudinary signature is invalid because the GitHub Actions credential set is inconsistent with the target Cloudinary account. The database failure follows because the script holds one async transaction open while each remote generation/upload may take 120 seconds, then the unit of work attempts a final commit after its connection has been closed.

## Evidence

- `.github/workflows/generate-catalog-meal-images.yml` injects repository/environment secrets independently of the deployed API runtime.
- `CloudinaryImageStore.save()` passes the SDK ordinary signed-upload fields: `format`, `overwrite`, `public_id`, and `timestamp`. Cloudinary signs these fields automatically. The reported string is therefore valid request shape; the account rejects the secret used to sign it.
- `scripts/generate_catalog_meal_images.py` opens `AsyncUnitOfWork` before selecting rows, retains it during Cloudflare + Cloudinary calls, and leaves the context to commit even when all attempts failed.
- `CloudflareWorkersImageGenerator` sends the configured Flux model through the base64 path, which necessarily uploads returned bytes to Cloudinary. This can differ from a working endpoint invocation only if it used a URL-returning model or different deployment credentials.

## Options Considered

1. Retry/reconnect the final DB commit. Rejected: it treats the symptom and still holds a database transaction during unbounded external I/O.
2. Change Cloudinary upload parameters. Rejected: the reported signed string matches Cloudinary's normal SDK contract; changing fields cannot repair a mismatched secret.
3. Short-lived database units plus safe configuration identity diagnostics. Selected: separates remote generation from persistence, preserves the endpoint contract, and directs the operational correction without exposing secrets.

## Approved Design

- Read catalog targets in a short-lived DB session, then close it before image generation.
- For each successful generation, open a new UoW only for conditional update and commit; retain the existing race-safe missing-image predicate.
- Make workflow startup validate non-empty secrets and emit only safe account/config fingerprints or metadata needed to distinguish mismatched Actions credentials; never print API keys, secrets, prompts, or URLs.
- Add unit coverage for failed generation, conditional persistence, and transaction scoping. Preserve the direct-upload endpoint and public contracts.
- Reconcile or rotate the GitHub Actions `production` environment's `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` as one matching set. This is a required operational action outside repository code.

## Success Criteria

- A failing Cloudinary upload increments `failed` and exits cleanly without a second DB commit error.
- A successful image is persisted only when the row still has no image URL.
- Database connections are never held during Cloudflare or Cloudinary requests.
- Signature mismatch diagnostics identify configuration mismatch safely, without disclosing sensitive values.
- The existing admin endpoint and signed direct-upload response contracts remain unchanged.

## Unresolved Questions

None. The production environment secret set must be corrected during rollout.
