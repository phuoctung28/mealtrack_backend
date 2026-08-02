# Catalog Image Generation Reliability Fix

**Date**: 2026-08-01
**Severity**: High
**Component**: Catalog image generation workflow
**Status**: Resolved

## What Happened

The catalog image job was failing in two different ways. Cloudinary uploads were coming back with invalid signatures, and the script was also holding one async database transaction open while each remote generation/upload could take a long time. That was a bad combination: the job could fail on the external call, then still trip over the database commit path on the way out.

## The Brutal Truth

This was self-inflicted. We tried to keep the whole workflow inside one unit of work and paid for it with fragile transaction scope, noisy failures, and useless retries. The embarrassing part is that the signature problem was not even a code-path mystery in the end, it was an operational mismatch between the GitHub production Cloudinary secret trio and the target account.

## Technical Details

The fix split read and write concerns. `scripts/generate_catalog_meal_images.py` now loads catalog rows in a short-lived `AsyncUnitOfWork`, closes it before any Cloudflare or Cloudinary I/O, and opens a fresh unit of work only for conditional persistence. Failures are categorized with safe error codes, so `invalid signature` is surfaced as `cloudinary_signature_invalid` without leaking secrets or payload data. `src/infra/adapters/cloudinary_image_store.py` now logs only the exception type, not the exception string.

Verification covered 57 focused tests, `py_compile`, Ruff, and reviewer approval. The workflow also now prints a safe reminder that `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` must be replaced together as one matching production set.

## What We Tried

We first treated the final commit failure as the bug. That was wrong. Retrying the commit would have hidden the real issue and kept the database connection hostage during remote work. We also rejected changing the Cloudinary request shape, because the signed upload parameters were already correct.

## Root Cause Analysis

Two root causes overlapped. First, we violated transaction boundaries by stretching a DB unit of work across unbounded network I/O. Second, production rollout was using a mismatched Cloudinary credential set, so the upload signature could never verify.

## Lessons Learned

External I/O and database lifetimes need to be separated by default. Also, secret drift must be treated as a deployment failure, not as an application bug that code can paper over.

## Next Steps

Reconcile the GitHub `production` Cloudinary secret trio as one matching set, with no value changes in code or docs. Keep the new tests and safe diagnostics in place, and treat any future signature error as a rollout check before touching the workflow again.
