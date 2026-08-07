# Integration Test Suite Design

**Date:** 2026-04-26 (Updated: 2026-04-27)  
**Status:** Approved  
**Author:** Claude + Alex

## Overview

Pre-release integration test suite that runs as a CI gate on merge to main. Tests all critical endpoints against real external services using the existing `mealtrack-e2e/` Playwright project.

## Goals

- Verify all critical user flows work before release (16+ flows across 3 tiers)
- Use existing `mealtrack-e2e/` repo (Playwright + TypeScript)
- Run against real external services (Neon, Firebase, Gemini, Cloudinary)
- Require manual approval before building production image

## Pipeline Flow

```
merge to main (mealtrack_backend)
     ↓
Build Test Container (Dockerfile.test)
     ↓
Run Unit Tests (in container)
     ↓
Trigger E2E Tests (mealtrack-e2e repo via repository_dispatch)
     ↓
E2E runs against staging/test environment
     ↓
Manual Approval (GitHub environment gate)
     ↓
Build & Push Production Image (ghcr.io)
```

## Test Scope (All Tiers)

### Tier 1: Must Pass — Core Data Pipeline

| Test File | Flow | Endpoints |
|-----------|------|-----------|
| `user-onboarding.spec.ts` | User sync | `POST /v1/users/sync` |
| | Check onboarding status | `GET /v1/users/firebase/{uid}/status` |
| | TDEE preview | `POST /v1/tdee/preview` |
| | Save onboarding profile | `POST /v1/user-profiles/` |
| | Mark onboarding complete | `PUT /v1/users/firebase/{uid}/onboarding/complete` |
| `meal-image-analysis.spec.ts` | Scan meal image | `POST /v1/meals/image/analyze` |
| | Get meal detail | `GET /v1/meals/{id}` |
| `meal-manual-entry.spec.ts` | Parse natural language | `POST /v1/meals/parse-text` |
| | Search foods | `GET /v1/foods/search` |
| | Create manual meal | `POST /v1/meals/manual` |
| `daily-tracking.spec.ts` | Daily activities feed | `GET /v1/activities/daily` |
| | Daily macro summary | `GET /v1/meals/daily/macros` |
| `webhooks.spec.ts` | RevenueCat INITIAL_PURCHASE | `POST /v1/webhooks/revenuecat` |
| | RevenueCat RENEWAL | `POST /v1/webhooks/revenuecat` |

### Tier 2: Must Pass — Feature Completeness

| Test File | Flow | Endpoints |
|-----------|------|-----------|
| `meal-suggestions.spec.ts` | Meal discovery | `POST /v1/meal-suggestions/discover` |
| | Recipe generation | `POST /v1/meal-suggestions/recipes` |
| | Save suggestion as meal | `POST /v1/meal-suggestions/save` |
| | Food image lookup | `GET /v1/meal-suggestions/image` |
| `meal-editing.spec.ts` | Edit meal ingredients | `PUT /v1/meals/{id}/ingredients` |
| | Delete meal | `DELETE /v1/meals/{id}` |
| `barcode.spec.ts` | Barcode lookup | `GET /v1/foods/barcode/{barcode}` |
| | Get food details | `GET /v1/foods/{fdc_id}/details` |
| `notifications.spec.ts` | Register FCM token | `POST /v1/notifications/tokens` |
| | Delete FCM token | `DELETE /v1/notifications/tokens` |
| | Update preferences | `PUT /v1/notifications/preferences` |

### Tier 3: Should Pass — Retention & Monetization

| Test File | Flow | Endpoints |
|-----------|------|-----------|
| `progress-tracking.spec.ts` | Logging streak | `GET /v1/meals/streak` |
| | Weekly breakdown | `GET /v1/meals/weekly/daily-breakdown` |
| | Weekly budget | `GET /v1/meals/weekly/budget` |
| `profile-management.spec.ts` | Get TDEE | `GET /v1/user-profiles/tdee` |
| | Update metrics | `POST /v1/user-profiles/metrics` |
| | Custom macros | `PUT /v1/user-profiles/custom-macros` |
| | Update timezone | `PUT /v1/users/timezone` |
| `referrals.spec.ts` | Validate referral code | `POST /v1/referrals/validate` |
| | Apply referral | `POST /v1/referrals/apply` |
| | Get my referral code | `GET /v1/referrals/my-code` |
| | Referral stats | `GET /v1/referrals/stats` |
| `saved-suggestions.spec.ts` | Bookmark suggestion | `POST /v1/saved-suggestions` |
| | List saved suggestions | `GET /v1/saved-suggestions` |
| | Remove bookmark | `DELETE /v1/saved-suggestions/{id}` |
| `cheat-days.spec.ts` | Mark cheat day | `POST /v1/cheat-days` |
| | Unmark cheat day | `DELETE /v1/cheat-days/{date}` |
| | Get cheat days | `GET /v1/cheat-days` |
| `account-deletion.spec.ts` | Delete account | `DELETE /v1/users/firebase/{uid}` |

## File Structure (mealtrack-e2e repo)

```
mealtrack-e2e/
├── src/
│   ├── auth/
│   │   └── firebase.ts           # Firebase custom token → ID token
│   ├── http/
│   │   └── client.ts             # API client with auth headers
│   ├── db/
│   │   ├── cleanup.ts            # DB cleanup functions
│   │   └── seed.ts               # Seed data population
│   └── config.ts                 # Environment config
├── tests/
│   ├── tier1/
│   │   ├── user-onboarding.spec.ts
│   │   ├── meal-image-analysis.spec.ts
│   │   ├── meal-manual-entry.spec.ts
│   │   ├── daily-tracking.spec.ts
│   │   └── webhooks.spec.ts
│   ├── tier2/
│   │   ├── meal-suggestions.spec.ts
│   │   ├── meal-editing.spec.ts
│   │   ├── barcode.spec.ts
│   │   └── notifications.spec.ts
│   ├── tier3/
│   │   ├── progress-tracking.spec.ts
│   │   ├── profile-management.spec.ts
│   │   ├── referrals.spec.ts
│   │   ├── saved-suggestions.spec.ts
│   │   ├── cheat-days.spec.ts
│   │   └── account-deletion.spec.ts
│   └── fixtures/
│       └── test-meal-image.jpg   # Sample image for analyze endpoint
├── playwright.config.ts
├── package.json
└── .github/
    └── workflows/
        └── e2e.yml               # Triggered by backend or manual
```

## Doppler Integration

**Project:** `mealtrack-e2e`  
**Config:** `ci`

**Secrets:**
```
# Database
DATABASE_URL                    # Neon test branch connection string

# Firebase
FIREBASE_WEB_API_KEY            # Firebase project API key
FIREBASE_SERVICE_ACCOUNT_JSON   # Service account for custom tokens
E2E_UID                         # Test user UID

# AI & Storage
GOOGLE_API_KEY                  # Gemini AI
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET

# RevenueCat (for webhook tests)
REVENUECAT_WEBHOOK_SECRET       # HMAC validation
```

## GitHub Actions Workflows

### Backend: release-pipeline.yml

```yaml
name: Release Pipeline

on:
  push:
    branches: [main]

env:
  TEST_IMAGE: mealtrack-backend:test-${{ github.sha }}
  PROD_IMAGE: ghcr.io/${{ github.repository }}:${{ github.sha }}

jobs:
  build-test-image:
    name: Build Test Image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -f Dockerfile.test -t ${{ env.TEST_IMAGE }} .
      - run: docker save ${{ env.TEST_IMAGE }} -o test-image.tar
      - uses: actions/upload-artifact@v4
        with:
          name: test-image
          path: test-image.tar

  unit-tests:
    name: Unit Tests
    needs: build-test-image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: test-image
      - run: docker load -i test-image.tar
      - run: |
          docker run --rm ${{ env.TEST_IMAGE }} \
            pytest tests/unit -v --cov=src --cov-fail-under=65

  trigger-e2e:
    name: Trigger E2E Tests
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - name: Trigger mealtrack-e2e workflow
        uses: peter-evans/repository-dispatch@v3
        with:
          token: ${{ secrets.E2E_REPO_PAT }}
          repository: phuoctung28/mealtrack-e2e
          event-type: run-e2e
          client-payload: '{"ref": "${{ github.sha }}", "triggered_by": "backend-release"}'

  wait-for-e2e:
    name: Wait for E2E Results
    needs: trigger-e2e
    runs-on: ubuntu-latest
    steps:
      - name: Wait for E2E workflow
        uses: fountainhead/action-wait-for-check@v1.2.0
        with:
          token: ${{ secrets.E2E_REPO_PAT }}
          repo: mealtrack-e2e
          ref: main
          checkName: E2E Tests
          timeoutSeconds: 900
          intervalSeconds: 30

  approval:
    name: Manual Approval
    needs: wait-for-e2e
    runs-on: ubuntu-latest
    environment: production
    steps:
      - run: echo "Approved for release"

  build-push-image:
    name: Build & Push Production Image
    needs: approval
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - run: |
          docker build -t ${{ env.PROD_IMAGE }} .
          docker tag ${{ env.PROD_IMAGE }} ghcr.io/${{ github.repository }}:latest
          docker push ${{ env.PROD_IMAGE }}
          docker push ghcr.io/${{ github.repository }}:latest
```

### E2E Repo: e2e.yml

```yaml
name: E2E Tests

on:
  repository_dispatch:
    types: [run-e2e]
  workflow_dispatch:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC

jobs:
  e2e:
    name: E2E Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Install Doppler CLI
        run: curl -Ls https://cli.doppler.com/install.sh | sh

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Cleanup test database
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          doppler run --project mealtrack-e2e --config ci -- \
            npx ts-node src/db/cleanup.ts

      - name: Seed test data
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          doppler run --project mealtrack-e2e --config ci -- \
            npx ts-node src/db/seed.ts

      - name: Run E2E tests
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
          E2E_CONFIRM_STAGING: '1'
        run: |
          doppler run --project mealtrack-e2e --config ci -- \
            npx playwright test --reporter=html

      - name: Upload test report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/

      - name: Cleanup test database
        if: always()
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          doppler run --project mealtrack-e2e --config ci -- \
            npx ts-node src/db/cleanup.ts
```

## Data Management

**Strategy:** Full cleanup + populate at start of each run

```typescript
// src/db/cleanup.ts
export async function cleanupTestData(pool: Pool): Promise<void> {
  await pool.query(`
    DELETE FROM meals WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@e2e-test.local');
    DELETE FROM user_profiles WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@e2e-test.local');
    DELETE FROM subscriptions WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@e2e-test.local');
    DELETE FROM saved_suggestions WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@e2e-test.local');
    DELETE FROM referrals WHERE referrer_id IN (SELECT id FROM users WHERE email LIKE '%@e2e-test.local');
    DELETE FROM users WHERE email LIKE '%@e2e-test.local';
  `);
}

// src/db/seed.ts
export async function seedTestData(pool: Pool): Promise<void> {
  // Create e2e test user (matches Firebase test user)
  await pool.query(`
    INSERT INTO users (id, firebase_uid, email, created_at)
    VALUES ($1, $2, $3, NOW())
    ON CONFLICT (firebase_uid) DO NOTHING
  `, [E2E_USER_ID, E2E_FIREBASE_UID, 'e2e-test@e2e-test.local']);
}
```

## External Services

| Service | Usage | Authentication |
|---------|-------|----------------|
| Neon PostgreSQL | Shared test branch | Connection string in Doppler |
| Firebase Auth | Custom token → ID token | Service account JSON in Doppler |
| Gemini AI | Real AI calls | API key in Doppler |
| Cloudinary | Real image storage | Credentials in Doppler |
| RevenueCat | Webhook signature validation | Secret in Doppler |

## Firebase Authentication (Existing Setup)

The `mealtrack-e2e` repo already has Firebase auth via custom tokens:

```typescript
// src/auth/firebase.ts
import admin from 'firebase-admin';

export async function getFirebaseIdToken(opts: {
  firebaseServiceAccountJson: string;
  firebaseWebApiKey: string;
  uid: string;
}): Promise<string> {
  // Initialize admin SDK
  const serviceAccount = JSON.parse(opts.firebaseServiceAccountJson);
  const app = admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
  });

  // Create custom token
  const customToken = await app.auth().createCustomToken(opts.uid);

  // Exchange for ID token via REST API
  const res = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=${opts.firebaseWebApiKey}`,
    {
      method: 'POST',
      body: JSON.stringify({ token: customToken, returnSecureToken: true })
    }
  );
  const data = await res.json();
  return data.idToken;
}
```

## Required Setup

### GitHub (Backend Repo)
1. Create `production` environment with required reviewers
2. Add `E2E_REPO_PAT` secret (PAT with repo dispatch permission)
3. Add `DOPPLER_TOKEN` secret (for unit tests if needed)

### GitHub (E2E Repo)
1. Add `DOPPLER_TOKEN` secret

### Doppler
1. Create project `mealtrack-e2e`
2. Create config `ci`
3. Add all secrets listed above
4. Generate service token for CI

### Firebase
1. Ensure test user exists with known UID
2. Service account JSON stored in Doppler

### Neon
1. Create dedicated test branch
2. Store connection string in Doppler

## Implementation Files

| Location | File | Purpose |
|----------|------|---------|
| Backend | `Dockerfile.test` | Test container with test deps |
| Backend | `.github/workflows/release-pipeline.yml` | CI pipeline with E2E trigger |
| E2E | `.github/workflows/e2e.yml` | E2E workflow |
| E2E | `src/db/cleanup.ts` | DB cleanup functions |
| E2E | `src/db/seed.ts` | Seed data functions |
| E2E | `tests/tier1/*.spec.ts` | Tier 1 critical tests |
| E2E | `tests/tier2/*.spec.ts` | Tier 2 feature tests |
| E2E | `tests/tier3/*.spec.ts` | Tier 3 retention tests |
| E2E | `tests/fixtures/test-meal-image.jpg` | Test image |
| E2E | `playwright.config.ts` | Playwright configuration |

## Test Execution Order

Tests run in tier order to fail fast on critical paths:

```typescript
// playwright.config.ts
export default defineConfig({
  projects: [
    { name: 'tier1', testDir: './tests/tier1' },
    { name: 'tier2', testDir: './tests/tier2', dependencies: ['tier1'] },
    { name: 'tier3', testDir: './tests/tier3', dependencies: ['tier2'] },
  ],
});
```

## Estimated Runtime

| Tier | Tests | Estimated Time |
|------|-------|----------------|
| Tier 1 | 5 files, ~15 tests | ~3-4 min |
| Tier 2 | 4 files, ~12 tests | ~2-3 min |
| Tier 3 | 6 files, ~18 tests | ~3-4 min |
| **Total** | **15 files, ~45 tests** | **~10 min** |
