# Integration Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive pre-release integration test suite with ~45 tests across 15 spec files, triggered by backend CI on merge to main.

**Architecture:** Two-repo approach — backend triggers E2E tests in `mealtrack-e2e` via repository_dispatch. Tests run in tiers (fail-fast on critical paths), with Doppler managing secrets. Full DB cleanup/seed before each run.

**Tech Stack:** Playwright + TypeScript (E2E), Docker (backend test container), GitHub Actions, Doppler, Neon PostgreSQL, Firebase Auth

---

## File Structure

### Backend Repo (mealtrack_backend)
```
Dockerfile.test                              # NEW - Test container
.github/workflows/release-pipeline.yml       # NEW - Release CI with E2E trigger
```

### E2E Repo (mealtrack-e2e)
```
src/
├── config.ts                                # MODIFY - Add new env vars
├── auth/firebase.ts                         # EXISTS - No changes needed
├── http/client.ts                           # MODIFY - Add PUT, DELETE, multipart
└── db/
    ├── connection.ts                        # NEW - Neon pool connection
    ├── cleanup.ts                           # NEW - DB cleanup functions
    └── seed.ts                              # NEW - Seed test data
tests/
├── tier1/
│   ├── user-onboarding.spec.ts              # NEW
│   ├── meal-image-analysis.spec.ts          # NEW
│   ├── meal-manual-entry.spec.ts            # NEW
│   ├── daily-tracking.spec.ts               # NEW
│   └── webhooks.spec.ts                     # NEW
├── tier2/
│   ├── meal-suggestions.spec.ts             # NEW
│   ├── meal-editing.spec.ts                 # NEW
│   ├── barcode.spec.ts                      # NEW
│   └── notifications.spec.ts                # NEW
├── tier3/
│   ├── progress-tracking.spec.ts            # NEW
│   ├── profile-management.spec.ts           # NEW
│   ├── referrals.spec.ts                    # NEW
│   ├── saved-suggestions.spec.ts            # NEW
│   ├── cheat-days.spec.ts                   # NEW
│   └── account-deletion.spec.ts             # NEW
├── fixtures/
│   └── test-meal-image.jpg                  # NEW - Sample food image
└── e2e/
    └── smoke.auth.spec.ts                   # EXISTS - Keep as smoke test
.github/workflows/e2e.yml                    # NEW - E2E workflow
playwright.config.ts                         # MODIFY - Tier-based projects
package.json                                 # MODIFY - Add pg dependency
```

---

## Task 1: Backend Dockerfile.test

**Files:**
- Create: `mealtrack_backend/Dockerfile.test`

- [ ] **Step 1: Create Dockerfile.test**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-test.txt

# Copy application and tests
COPY src/ ./src/
COPY tests/ ./tests/
COPY pytest.ini pyproject.toml alembic.ini ./
COPY migrations/ ./migrations/

# Set Python path
ENV PYTHONPATH=/app

# Default command: run unit tests
CMD ["pytest", "tests/unit", "-v", "--tb=short"]
```

- [ ] **Step 2: Verify Dockerfile builds**

Run:
```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack_backend
docker build -f Dockerfile.test -t mealtrack-backend:test .
```

Expected: Build completes successfully

- [ ] **Step 3: Verify tests run in container**

Run:
```bash
docker run --rm mealtrack-backend:test pytest tests/unit -v --co -q | head -20
```

Expected: Shows collected test list

- [ ] **Step 4: Commit**

```bash
git add Dockerfile.test
git commit -m "build: add Dockerfile.test for CI test container"
```

---

## Task 2: Backend Release Pipeline Workflow

**Files:**
- Create: `mealtrack_backend/.github/workflows/release-pipeline.yml`

- [ ] **Step 1: Create release-pipeline.yml**

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
    name: 🔨 Build Test Image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build test image
        run: docker build -f Dockerfile.test -t ${{ env.TEST_IMAGE }} .

      - name: Save image as artifact
        run: docker save ${{ env.TEST_IMAGE }} -o test-image.tar

      - uses: actions/upload-artifact@v4
        with:
          name: test-image
          path: test-image.tar
          retention-days: 1

  unit-tests:
    name: 🧪 Unit Tests
    needs: build-test-image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: test-image

      - name: Load test image
        run: docker load -i test-image.tar

      - name: Run unit tests
        run: |
          docker run --rm ${{ env.TEST_IMAGE }} \
            pytest tests/unit -v --cov=src --cov-fail-under=65

  trigger-e2e:
    name: 🚀 Trigger E2E Tests
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
    name: ⏳ Wait for E2E Results
    needs: trigger-e2e
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - name: Wait for E2E workflow completion
        uses: fountainhead/action-wait-for-check@v1.2.0
        with:
          token: ${{ secrets.E2E_REPO_PAT }}
          repo: mealtrack-e2e
          ref: main
          checkName: e2e
          timeoutSeconds: 900
          intervalSeconds: 30

  approval:
    name: ✅ Manual Approval
    needs: wait-for-e2e
    runs-on: ubuntu-latest
    environment: production
    steps:
      - run: echo "Release approved"

  build-push-image:
    name: 📦 Build & Push Production Image
    needs: approval
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        run: |
          docker build -t ${{ env.PROD_IMAGE }} .
          docker tag ${{ env.PROD_IMAGE }} ghcr.io/${{ github.repository }}:latest
          docker push ${{ env.PROD_IMAGE }}
          docker push ghcr.io/${{ github.repository }}:latest
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release-pipeline.yml
git commit -m "ci: add release pipeline with E2E gate and manual approval"
```

---

## Task 3: E2E Repo - Update package.json

**Files:**
- Modify: `mealtrack-e2e/package.json`

- [ ] **Step 1: Add pg and ts-node dependencies**

```json
{
  "name": "mealtrack-e2e",
  "version": "0.1.0",
  "private": true,
  "description": "Staging-only API E2E smoke tests for Mealtrack backend (Firebase auth, real environment).",
  "type": "module",
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "test": "playwright test",
    "test:tier1": "playwright test --project=tier1",
    "test:tier2": "playwright test --project=tier2",
    "test:tier3": "playwright test --project=tier3",
    "db:cleanup": "npx ts-node --esm src/db/cleanup.ts",
    "db:seed": "npx ts-node --esm src/db/seed.ts",
    "lint": "eslint .",
    "format": "prettier -w ."
  },
  "devDependencies": {
    "@eslint/js": "^9.0.0",
    "@playwright/test": "^1.55.0",
    "@types/node": "^22.0.0",
    "@types/pg": "^8.11.0",
    "eslint": "^9.0.0",
    "globals": "^16.0.0",
    "prettier": "^3.0.0",
    "ts-node": "^10.9.0",
    "typescript": "^5.0.0"
  },
  "dependencies": {
    "firebase-admin": "^13.0.0",
    "pg": "^8.13.0"
  }
}
```

- [ ] **Step 2: Install dependencies**

Run:
```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack-e2e
npm install
```

- [ ] **Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "deps: add pg for database operations and ts-node for scripts"
```

---

## Task 4: E2E Repo - Update Config

**Files:**
- Modify: `mealtrack-e2e/src/config.ts`

- [ ] **Step 1: Update config.ts with all required env vars**

```typescript
const STAGING_ALLOWLIST = new Set<string>([
  'https://mealtrack-backend-main.onrender.com',
  'http://localhost:8000'
]);

export type Env = {
  baseUrl: string;
  firebaseWebApiKey: string;
  firebaseServiceAccountJson: string;
  e2eUid: string;
  e2eConfirmStaging: boolean;
  databaseUrl: string;
  revenuecatWebhookSecret: string;
};

export function readEnv(): Env {
  const baseUrlRaw = (process.env.E2E_BASE_URL ?? '').trim();
  if (!baseUrlRaw) throw new Error('Missing E2E_BASE_URL');

  const baseUrl = baseUrlRaw.replace(/\/+$/, '');
  if (!STAGING_ALLOWLIST.has(baseUrl)) {
    throw new Error(
      `E2E_BASE_URL is not allowlisted. Got: ${baseUrl}. Allowed: ${Array.from(STAGING_ALLOWLIST).join(', ')}`
    );
  }

  const firebaseWebApiKey = (process.env.FIREBASE_WEB_API_KEY ?? '').trim();
  if (!firebaseWebApiKey) throw new Error('Missing FIREBASE_WEB_API_KEY');

  const firebaseServiceAccountJson = (process.env.FIREBASE_SERVICE_ACCOUNT_JSON ?? '').trim();
  if (!firebaseServiceAccountJson) throw new Error('Missing FIREBASE_SERVICE_ACCOUNT_JSON');

  const e2eUid = (process.env.E2E_UID ?? 'e2e-bot').trim();
  if (!e2eUid) throw new Error('Missing/empty E2E_UID');

  const databaseUrl = (process.env.DATABASE_URL ?? '').trim();
  if (!databaseUrl) throw new Error('Missing DATABASE_URL');

  const revenuecatWebhookSecret = (process.env.REVENUECAT_WEBHOOK_SECRET ?? '').trim();

  const e2eConfirmStaging = (process.env.E2E_CONFIRM_STAGING ?? '') === '1';
  if (process.env.CI && !e2eConfirmStaging) {
    throw new Error('Refusing to run in CI without E2E_CONFIRM_STAGING=1');
  }

  return {
    baseUrl,
    firebaseWebApiKey,
    firebaseServiceAccountJson,
    e2eUid,
    e2eConfirmStaging,
    databaseUrl,
    revenuecatWebhookSecret
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add src/config.ts
git commit -m "config: add DATABASE_URL and REVENUECAT_WEBHOOK_SECRET"
```

---

## Task 5: E2E Repo - Extend HTTP Client

**Files:**
- Modify: `mealtrack-e2e/src/http/client.ts`

- [ ] **Step 1: Add PUT, DELETE, and multipart methods**

```typescript
import { request as playwrightRequest } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

export type ApiResponse = {
  status: number;
  json: () => Promise<unknown>;
  text: () => Promise<string>;
};

export type ApiClient = {
  get: (path: string) => Promise<ApiResponse>;
  post: (path: string, body?: unknown) => Promise<ApiResponse>;
  put: (path: string, body?: unknown) => Promise<ApiResponse>;
  delete: (path: string) => Promise<ApiResponse>;
  postMultipart: (path: string, filePath: string, fields?: Record<string, string>) => Promise<ApiResponse>;
};

export async function createApiClient(args: {
  baseUrl: string;
  idToken: string;
  e2eRunId: string;
}): Promise<ApiClient> {
  const ctx = await playwrightRequest.newContext({
    baseURL: args.baseUrl,
    extraHTTPHeaders: {
      authorization: `Bearer ${args.idToken}`,
      'x-e2e-run-id': args.e2eRunId
    }
  });

  const wrapResponse = (res: Awaited<ReturnType<typeof ctx.get>>): ApiResponse => ({
    status: res.status(),
    json: async () => await res.json(),
    text: async () => await res.text()
  });

  return {
    get: async (urlPath: string) => {
      const res = await ctx.get(urlPath);
      return wrapResponse(res);
    },

    post: async (urlPath: string, body?: unknown) => {
      const res = await ctx.post(urlPath, {
        data: body,
        headers: { 'content-type': 'application/json' }
      });
      return wrapResponse(res);
    },

    put: async (urlPath: string, body?: unknown) => {
      const res = await ctx.put(urlPath, {
        data: body,
        headers: { 'content-type': 'application/json' }
      });
      return wrapResponse(res);
    },

    delete: async (urlPath: string) => {
      const res = await ctx.delete(urlPath);
      return wrapResponse(res);
    },

    postMultipart: async (urlPath: string, filePath: string, fields?: Record<string, string>) => {
      const fileBuffer = fs.readFileSync(filePath);
      const fileName = path.basename(filePath);
      const mimeType = filePath.endsWith('.png') ? 'image/png' : 'image/jpeg';

      const res = await ctx.post(urlPath, {
        multipart: {
          file: {
            name: fileName,
            mimeType,
            buffer: fileBuffer
          },
          ...fields
        }
      });
      return wrapResponse(res);
    }
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add src/http/client.ts
git commit -m "feat: extend API client with PUT, DELETE, and multipart support"
```

---

## Task 6: E2E Repo - Database Connection

**Files:**
- Create: `mealtrack-e2e/src/db/connection.ts`

- [ ] **Step 1: Create connection.ts**

```typescript
import pg from 'pg';

const { Pool } = pg;

let pool: pg.Pool | null = null;

export function getPool(databaseUrl: string): pg.Pool {
  if (!pool) {
    pool = new Pool({
      connectionString: databaseUrl,
      ssl: { rejectUnauthorized: false }
    });
  }
  return pool;
}

export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}
```

- [ ] **Step 2: Commit**

```bash
mkdir -p src/db
git add src/db/connection.ts
git commit -m "feat: add database connection pool utility"
```

---

## Task 7: E2E Repo - Database Cleanup

**Files:**
- Create: `mealtrack-e2e/src/db/cleanup.ts`

- [ ] **Step 1: Create cleanup.ts**

```typescript
import { getPool, closePool } from './connection.js';
import { readEnv } from '../config.js';

const E2E_USER_MARKER = '@e2e-test.local';

export async function cleanupTestData(databaseUrl: string): Promise<void> {
  const pool = getPool(databaseUrl);

  console.log('Starting E2E test data cleanup...');

  // Delete in dependency order (children before parents)
  const tables = [
    'cheat_days',
    'saved_suggestions', 
    'fcm_tokens',
    'notification_preferences',
    'referral_conversions',
    'referrals',
    'subscriptions',
    'meal_images',
    'food_items',
    'meals',
    'activities',
    'user_profiles',
    'users'
  ];

  for (const table of tables) {
    try {
      if (table === 'users') {
        const result = await pool.query(
          `DELETE FROM ${table} WHERE email LIKE $1`,
          [`%${E2E_USER_MARKER}`]
        );
        console.log(`  ${table}: deleted ${result.rowCount} rows`);
      } else if (['user_profiles', 'meals', 'activities', 'subscriptions', 'referrals', 'fcm_tokens', 'notification_preferences', 'saved_suggestions', 'cheat_days'].includes(table)) {
        const result = await pool.query(
          `DELETE FROM ${table} WHERE user_id IN (SELECT id FROM users WHERE email LIKE $1)`,
          [`%${E2E_USER_MARKER}`]
        );
        console.log(`  ${table}: deleted ${result.rowCount} rows`);
      } else if (table === 'referral_conversions') {
        const result = await pool.query(
          `DELETE FROM ${table} WHERE referral_id IN (
            SELECT id FROM referrals WHERE referrer_id IN (SELECT id FROM users WHERE email LIKE $1)
          )`,
          [`%${E2E_USER_MARKER}`]
        );
        console.log(`  ${table}: deleted ${result.rowCount} rows`);
      } else if (['meal_images', 'food_items'].includes(table)) {
        const result = await pool.query(
          `DELETE FROM ${table} WHERE meal_id IN (
            SELECT id FROM meals WHERE user_id IN (SELECT id FROM users WHERE email LIKE $1)
          )`,
          [`%${E2E_USER_MARKER}`]
        );
        console.log(`  ${table}: deleted ${result.rowCount} rows`);
      }
    } catch (err) {
      console.log(`  ${table}: skipped (table may not exist)`);
    }
  }

  console.log('Cleanup complete.');
}

// CLI entry point
if (process.argv[1]?.endsWith('cleanup.ts') || process.argv[1]?.endsWith('cleanup.js')) {
  const env = readEnv();
  cleanupTestData(env.databaseUrl)
    .then(() => closePool())
    .then(() => process.exit(0))
    .catch((err) => {
      console.error('Cleanup failed:', err);
      process.exit(1);
    });
}
```

- [ ] **Step 2: Commit**

```bash
git add src/db/cleanup.ts
git commit -m "feat: add E2E database cleanup utility"
```

---

## Task 8: E2E Repo - Database Seed

**Files:**
- Create: `mealtrack-e2e/src/db/seed.ts`

- [ ] **Step 1: Create seed.ts**

```typescript
import { getPool, closePool } from './connection.js';
import { readEnv } from '../config.js';
import crypto from 'node:crypto';

const E2E_USER_EMAIL = 'e2e-test@e2e-test.local';

export async function seedTestData(databaseUrl: string, firebaseUid: string): Promise<{ userId: string }> {
  const pool = getPool(databaseUrl);

  console.log('Seeding E2E test data...');

  const userId = crypto.randomUUID();

  // Create test user
  await pool.query(
    `INSERT INTO users (id, firebase_uid, email, created_at, updated_at, is_active, onboarding_completed)
     VALUES ($1, $2, $3, NOW(), NOW(), true, false)
     ON CONFLICT (firebase_uid) DO UPDATE SET
       email = EXCLUDED.email,
       updated_at = NOW()
     RETURNING id`,
    [userId, firebaseUid, E2E_USER_EMAIL]
  );

  console.log(`  Created/updated user: ${userId} (firebase_uid: ${firebaseUid})`);
  console.log('Seed complete.');

  return { userId };
}

// CLI entry point
if (process.argv[1]?.endsWith('seed.ts') || process.argv[1]?.endsWith('seed.js')) {
  const env = readEnv();
  seedTestData(env.databaseUrl, env.e2eUid)
    .then(() => closePool())
    .then(() => process.exit(0))
    .catch((err) => {
      console.error('Seed failed:', err);
      process.exit(1);
    });
}
```

- [ ] **Step 2: Commit**

```bash
git add src/db/seed.ts
git commit -m "feat: add E2E database seed utility"
```

---

## Task 9: E2E Repo - Update Playwright Config

**Files:**
- Modify: `mealtrack-e2e/playwright.config.ts`

- [ ] **Step 1: Update playwright.config.ts with tier-based projects**

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // Run tests sequentially within each tier
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 60000, // 60s per test for AI endpoints
  reporter: process.env.CI 
    ? [['github'], ['html', { open: 'never' }]] 
    : [['list'], ['html']],
  use: {
    trace: 'retain-on-failure'
  },
  projects: [
    {
      name: 'tier1',
      testDir: './tests/tier1',
      testMatch: '**/*.spec.ts'
    },
    {
      name: 'tier2',
      testDir: './tests/tier2',
      testMatch: '**/*.spec.ts',
      dependencies: ['tier1']
    },
    {
      name: 'tier3',
      testDir: './tests/tier3',
      testMatch: '**/*.spec.ts',
      dependencies: ['tier2']
    },
    {
      name: 'smoke',
      testDir: './tests/e2e',
      testMatch: '**/*.spec.ts'
    }
  ]
});
```

- [ ] **Step 2: Commit**

```bash
git add playwright.config.ts
git commit -m "config: add tier-based test projects with dependencies"
```

---

## Task 10: E2E Repo - Test Fixture Image

**Files:**
- Create: `mealtrack-e2e/tests/fixtures/test-meal-image.jpg`

- [ ] **Step 1: Create fixtures directory and add test image**

Run:
```bash
mkdir -p tests/fixtures
# Download a sample food image (or copy an existing one)
curl -L "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400" -o tests/fixtures/test-meal-image.jpg
```

- [ ] **Step 2: Commit**

```bash
git add tests/fixtures/test-meal-image.jpg
git commit -m "test: add sample meal image fixture"
```

---

## Task 11: Tier 1 - User Onboarding Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier1/user-onboarding.spec.ts`

- [ ] **Step 1: Create user-onboarding.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';
import { cleanupTestData } from '../../src/db/cleanup.js';
import { seedTestData } from '../../src/db/seed.js';

test.describe('User Onboarding Flow @tier1', () => {
  let api: ApiClient;
  let env: ReturnType<typeof readEnv>;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    env = readEnv();
    
    // Cleanup and seed
    await cleanupTestData(env.databaseUrl);
    await seedTestData(env.databaseUrl, env.e2eUid);

    // Get auth token
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });

    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('POST /v1/users/sync - syncs user from Firebase', async () => {
    const res = await api.post('/v1/users/sync', {
      firebase_uid: env.e2eUid,
      email: 'e2e-test@e2e-test.local',
      provider: 'custom'
    });

    expect(res.status).toBe(200);
    const body = await res.json() as { user_id: string; created: boolean };
    expect(body.user_id).toBeTruthy();
  });

  test('GET /v1/users/firebase/{uid}/status - checks onboarding status', async () => {
    const res = await api.get(`/v1/users/firebase/${env.e2eUid}/status`);

    expect(res.status).toBe(200);
    const body = await res.json() as { onboarding_completed: boolean };
    expect(body.onboarding_completed).toBe(false);
  });

  test('POST /v1/tdee/preview - calculates TDEE preview', async () => {
    const res = await api.post('/v1/tdee/preview', {
      weight_kg: 70,
      height_cm: 175,
      age: 30,
      gender: 'male',
      activity_level: 'moderate',
      fitness_goal: 'maintain'
    });

    expect(res.status).toBe(200);
    const body = await res.json() as { tdee: number; bmr: number };
    expect(body.tdee).toBeGreaterThan(1500);
    expect(body.bmr).toBeGreaterThan(1200);
  });

  test('POST /v1/user-profiles/ - saves onboarding profile', async () => {
    const res = await api.post('/v1/user-profiles/', {
      weight_kg: 70,
      height_cm: 175,
      age: 30,
      gender: 'male',
      activity_level: 'moderate',
      fitness_goal: 'maintain',
      dietary_preferences: ['none']
    });

    expect(res.status).toBe(201);
    const body = await res.json() as { id: string; tdee: number };
    expect(body.id).toBeTruthy();
    expect(body.tdee).toBeGreaterThan(0);
  });

  test('PUT /v1/users/firebase/{uid}/onboarding/complete - marks onboarding complete', async () => {
    const res = await api.put(`/v1/users/firebase/${env.e2eUid}/onboarding/complete`, {});

    expect(res.status).toBe(200);
    const body = await res.json() as { onboarding_completed: boolean };
    expect(body.onboarding_completed).toBe(true);
  });
});
```

- [ ] **Step 2: Create tier1 directory**

Run:
```bash
mkdir -p tests/tier1
```

- [ ] **Step 3: Commit**

```bash
git add tests/tier1/user-onboarding.spec.ts
git commit -m "test: add tier1 user onboarding flow tests"
```

---

## Task 12: Tier 1 - Meal Image Analysis Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier1/meal-image-analysis.spec.ts`

- [ ] **Step 1: Create meal-image-analysis.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import path from 'node:path';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Meal Image Analysis Flow @tier1', () => {
  let api: ApiClient;
  let env: ReturnType<typeof readEnv>;
  let createdMealId: string;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('POST /v1/meals/image/analyze - analyzes meal from image', async () => {
    const imagePath = path.join(process.cwd(), 'tests/fixtures/test-meal-image.jpg');
    
    const res = await api.postMultipart('/v1/meals/image/analyze', imagePath);

    // May return 200 (success) or 400 (not food image) depending on image
    expect([200, 400]).toContain(res.status);
    
    if (res.status === 200) {
      const body = await res.json() as { id: string; status: string; food_items: unknown[] };
      expect(body.id).toBeTruthy();
      expect(body.status).toBe('ready');
      createdMealId = body.id;
    }
  });

  test('GET /v1/meals/{id} - gets meal detail', async () => {
    // Skip if no meal was created
    test.skip(!createdMealId, 'No meal created from previous test');

    const res = await api.get(`/v1/meals/${createdMealId}`);

    expect(res.status).toBe(200);
    const body = await res.json() as { id: string; food_items: unknown[] };
    expect(body.id).toBe(createdMealId);
    expect(body.food_items).toBeDefined();
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier1/meal-image-analysis.spec.ts
git commit -m "test: add tier1 meal image analysis tests"
```

---

## Task 13: Tier 1 - Manual Meal Entry Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier1/meal-manual-entry.spec.ts`

- [ ] **Step 1: Create meal-manual-entry.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Manual Meal Entry Flow @tier1', () => {
  let api: ApiClient;
  let createdMealId: string;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('POST /v1/meals/parse-text - parses natural language meal description', async () => {
    const res = await api.post('/v1/meals/parse-text', {
      text: '2 scrambled eggs and a slice of toast'
    });

    expect(res.status).toBe(200);
    const body = await res.json() as { items: unknown[]; total_nutrition: { calories: number } };
    expect(body.items.length).toBeGreaterThan(0);
    expect(body.total_nutrition.calories).toBeGreaterThan(0);
  });

  test('GET /v1/foods/search - searches foods by name', async () => {
    const res = await api.get('/v1/foods/search?q=chicken%20breast');

    expect(res.status).toBe(200);
    const body = await res.json() as { foods: Array<{ fdc_id: string; name: string }> };
    expect(body.foods.length).toBeGreaterThan(0);
  });

  test('POST /v1/meals/manual - creates manual meal from foods', async () => {
    const today = new Date().toISOString().split('T')[0];
    
    const res = await api.post('/v1/meals/manual', {
      target_date: today,
      items: [
        {
          name: 'Scrambled Eggs',
          quantity: 2,
          unit: 'large',
          custom_nutrition: {
            calories: 180,
            protein_g: 12,
            carbs_g: 2,
            fat_g: 14
          }
        }
      ]
    });

    expect(res.status).toBe(201);
    const body = await res.json() as { id: string; status: string };
    expect(body.id).toBeTruthy();
    createdMealId = body.id;
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier1/meal-manual-entry.spec.ts
git commit -m "test: add tier1 manual meal entry tests"
```

---

## Task 14: Tier 1 - Daily Tracking Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier1/daily-tracking.spec.ts`

- [ ] **Step 1: Create daily-tracking.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Daily Tracking Flow @tier1', () => {
  let api: ApiClient;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('GET /v1/activities/daily - gets daily activities feed', async () => {
    const today = new Date().toISOString().split('T')[0];
    const res = await api.get(`/v1/activities/daily?date=${today}`);

    expect(res.status).toBe(200);
    const body = await res.json() as { activities: unknown[] };
    expect(Array.isArray(body.activities)).toBe(true);
  });

  test('GET /v1/meals/daily/macros - gets daily macro summary', async () => {
    const today = new Date().toISOString().split('T')[0];
    const res = await api.get(`/v1/meals/daily/macros?date=${today}`);

    expect(res.status).toBe(200);
    const body = await res.json() as {
      consumed: { calories: number };
      target: { calories: number };
    };
    expect(body.consumed).toBeDefined();
    expect(body.target).toBeDefined();
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier1/daily-tracking.spec.ts
git commit -m "test: add tier1 daily tracking tests"
```

---

## Task 15: Tier 1 - Webhooks Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier1/webhooks.spec.ts`

- [ ] **Step 1: Create webhooks.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { request } from '@playwright/test';

test.describe('RevenueCat Webhooks @tier1', () => {
  let env: ReturnType<typeof readEnv>;

  test.beforeAll(() => {
    env = readEnv();
  });

  test('POST /v1/webhooks/revenuecat - handles INITIAL_PURCHASE', async () => {
    test.skip(!env.revenuecatWebhookSecret, 'REVENUECAT_WEBHOOK_SECRET not configured');

    const ctx = await request.newContext({ baseURL: env.baseUrl });
    
    const payload = {
      api_version: '1.0',
      event: {
        type: 'INITIAL_PURCHASE',
        app_user_id: env.e2eUid,
        product_id: 'premium_monthly',
        purchased_at_ms: Date.now(),
        expiration_at_ms: Date.now() + 30 * 24 * 60 * 60 * 1000
      }
    };

    // Create HMAC signature
    const hmac = crypto.createHmac('sha256', env.revenuecatWebhookSecret);
    hmac.update(JSON.stringify(payload));
    const signature = hmac.digest('hex');

    const res = await ctx.post('/v1/webhooks/revenuecat', {
      data: payload,
      headers: {
        'content-type': 'application/json',
        'authorization': `Bearer ${signature}`
      }
    });

    // 200 = processed, 400 = validation error (user may not exist)
    expect([200, 400]).toContain(res.status());
  });

  test('POST /v1/webhooks/revenuecat - handles RENEWAL', async () => {
    test.skip(!env.revenuecatWebhookSecret, 'REVENUECAT_WEBHOOK_SECRET not configured');

    const ctx = await request.newContext({ baseURL: env.baseUrl });
    
    const payload = {
      api_version: '1.0',
      event: {
        type: 'RENEWAL',
        app_user_id: env.e2eUid,
        product_id: 'premium_monthly',
        purchased_at_ms: Date.now(),
        expiration_at_ms: Date.now() + 30 * 24 * 60 * 60 * 1000
      }
    };

    const hmac = crypto.createHmac('sha256', env.revenuecatWebhookSecret);
    hmac.update(JSON.stringify(payload));
    const signature = hmac.digest('hex');

    const res = await ctx.post('/v1/webhooks/revenuecat', {
      data: payload,
      headers: {
        'content-type': 'application/json',
        'authorization': `Bearer ${signature}`
      }
    });

    expect([200, 400]).toContain(res.status());
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier1/webhooks.spec.ts
git commit -m "test: add tier1 RevenueCat webhook tests"
```

---

## Task 16: Tier 2 - Meal Suggestions Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier2/meal-suggestions.spec.ts`

- [ ] **Step 1: Create meal-suggestions.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Meal Suggestions Flow @tier2', () => {
  let api: ApiClient;
  let discoveredMeals: Array<{ id: string; name: string }> = [];
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('POST /v1/meal-suggestions/discover - discovers meal suggestions', async () => {
    const res = await api.post('/v1/meal-suggestions/discover', {
      meal_type: 'lunch',
      count: 3
    });

    expect(res.status).toBe(200);
    const body = await res.json() as { suggestions: Array<{ id: string; name: string }> };
    expect(body.suggestions.length).toBeGreaterThan(0);
    discoveredMeals = body.suggestions;
  });

  test('POST /v1/meal-suggestions/recipes - generates recipes for selected meals', async () => {
    test.skip(discoveredMeals.length === 0, 'No meals discovered');

    const res = await api.post('/v1/meal-suggestions/recipes', {
      suggestion_ids: [discoveredMeals[0].id]
    });

    expect(res.status).toBe(200);
    const body = await res.json() as { recipes: Array<{ id: string; ingredients: unknown[] }> };
    expect(body.recipes.length).toBeGreaterThan(0);
    expect(body.recipes[0].ingredients).toBeDefined();
  });

  test('GET /v1/meal-suggestions/image - gets food image', async () => {
    const res = await api.get('/v1/meal-suggestions/image?q=grilled%20chicken');

    // 200 = image found, 204 = not found
    expect([200, 204]).toContain(res.status);
  });

  test('POST /v1/meal-suggestions/save - saves suggestion as meal', async () => {
    test.skip(discoveredMeals.length === 0, 'No meals discovered');

    const today = new Date().toISOString().split('T')[0];
    const res = await api.post('/v1/meal-suggestions/save', {
      suggestion_id: discoveredMeals[0].id,
      target_date: today
    });

    expect(res.status).toBe(201);
    const body = await res.json() as { meal_id: string };
    expect(body.meal_id).toBeTruthy();
  });
});
```

- [ ] **Step 2: Create tier2 directory**

Run:
```bash
mkdir -p tests/tier2
```

- [ ] **Step 3: Commit**

```bash
git add tests/tier2/meal-suggestions.spec.ts
git commit -m "test: add tier2 meal suggestions tests"
```

---

## Task 17: Tier 2 - Meal Editing Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier2/meal-editing.spec.ts`

- [ ] **Step 1: Create meal-editing.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Meal Editing Flow @tier2', () => {
  let api: ApiClient;
  let testMealId: string;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });

    // Create a meal to edit
    const today = new Date().toISOString().split('T')[0];
    const res = await api.post('/v1/meals/manual', {
      target_date: today,
      items: [{
        name: 'Test Meal for Editing',
        quantity: 1,
        unit: 'serving',
        custom_nutrition: { calories: 500, protein_g: 30, carbs_g: 40, fat_g: 20 }
      }]
    });
    const body = await res.json() as { id: string };
    testMealId = body.id;
  });

  test('PUT /v1/meals/{id}/ingredients - edits meal ingredients', async () => {
    test.skip(!testMealId, 'No test meal created');

    const res = await api.put(`/v1/meals/${testMealId}/ingredients`, {
      changes: [{
        action: 'add',
        item: {
          name: 'Added Item',
          quantity: 1,
          unit: 'piece',
          custom_nutrition: { calories: 100, protein_g: 5, carbs_g: 10, fat_g: 5 }
        }
      }]
    });

    expect(res.status).toBe(200);
    const body = await res.json() as { id: string; food_items: unknown[] };
    expect(body.food_items.length).toBeGreaterThan(1);
  });

  test('DELETE /v1/meals/{id} - deletes meal (soft delete)', async () => {
    test.skip(!testMealId, 'No test meal created');

    const res = await api.delete(`/v1/meals/${testMealId}`);

    expect(res.status).toBe(200);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier2/meal-editing.spec.ts
git commit -m "test: add tier2 meal editing tests"
```

---

## Task 18: Tier 2 - Barcode Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier2/barcode.spec.ts`

- [ ] **Step 1: Create barcode.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Barcode Lookup Flow @tier2', () => {
  let api: ApiClient;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('GET /v1/foods/barcode/{barcode} - looks up product by barcode', async () => {
    // Use a known barcode (Coca-Cola)
    const res = await api.get('/v1/foods/barcode/5449000000996');

    // 200 = found, 404 = not in database
    expect([200, 404]).toContain(res.status);
    
    if (res.status === 200) {
      const body = await res.json() as { name: string; nutrition: unknown };
      expect(body.name).toBeTruthy();
    }
  });

  test('GET /v1/foods/{fdc_id}/details - gets food details', async () => {
    // First search for a food to get an FDC ID
    const searchRes = await api.get('/v1/foods/search?q=apple');
    const searchBody = await searchRes.json() as { foods: Array<{ fdc_id: string }> };
    
    test.skip(searchBody.foods.length === 0, 'No foods found in search');

    const fdcId = searchBody.foods[0].fdc_id;
    const res = await api.get(`/v1/foods/${fdcId}/details`);

    expect(res.status).toBe(200);
    const body = await res.json() as { fdc_id: string; nutrients: unknown };
    expect(body.fdc_id).toBe(fdcId);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier2/barcode.spec.ts
git commit -m "test: add tier2 barcode lookup tests"
```

---

## Task 19: Tier 2 - Notifications Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier2/notifications.spec.ts`

- [ ] **Step 1: Create notifications.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Notifications Flow @tier2', () => {
  let api: ApiClient;
  const e2eRunId = crypto.randomUUID();
  const testFcmToken = `e2e-test-token-${crypto.randomUUID()}`;

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('POST /v1/notifications/tokens - registers FCM token', async () => {
    const res = await api.post('/v1/notifications/tokens', {
      token: testFcmToken,
      device_type: 'ios',
      timezone: 'America/New_York'
    });

    expect(res.status).toBe(201);
  });

  test('PUT /v1/notifications/preferences - updates notification preferences', async () => {
    const res = await api.put('/v1/notifications/preferences', {
      breakfast_reminder: true,
      breakfast_time: '08:00',
      lunch_reminder: true,
      lunch_time: '12:00',
      dinner_reminder: false,
      daily_summary: true
    });

    expect(res.status).toBe(200);
    const body = await res.json() as { breakfast_reminder: boolean };
    expect(body.breakfast_reminder).toBe(true);
  });

  test('DELETE /v1/notifications/tokens - deletes FCM token', async () => {
    const res = await api.delete('/v1/notifications/tokens');

    expect(res.status).toBe(200);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier2/notifications.spec.ts
git commit -m "test: add tier2 notifications tests"
```

---

## Task 20: Tier 3 - Progress Tracking Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier3/progress-tracking.spec.ts`

- [ ] **Step 1: Create progress-tracking.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Progress Tracking @tier3', () => {
  let api: ApiClient;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('GET /v1/meals/streak - gets logging streak', async () => {
    const res = await api.get('/v1/meals/streak');

    expect(res.status).toBe(200);
    const body = await res.json() as { current_streak: number; best_streak: number };
    expect(body.current_streak).toBeGreaterThanOrEqual(0);
    expect(body.best_streak).toBeGreaterThanOrEqual(0);
  });

  test('GET /v1/meals/weekly/daily-breakdown - gets weekly breakdown', async () => {
    const monday = getMonday(new Date()).toISOString().split('T')[0];
    const res = await api.get(`/v1/meals/weekly/daily-breakdown?week_start=${monday}`);

    expect(res.status).toBe(200);
    const body = await res.json() as { days: Array<{ date: string }> };
    expect(body.days.length).toBe(7);
  });

  test('GET /v1/meals/weekly/budget - gets weekly budget', async () => {
    const monday = getMonday(new Date()).toISOString().split('T')[0];
    const res = await api.get(`/v1/meals/weekly/budget?week_start=${monday}`);

    expect(res.status).toBe(200);
    const body = await res.json() as { remaining_days: number; adjusted_daily_target: unknown };
    expect(body.remaining_days).toBeGreaterThan(0);
  });
});

function getMonday(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(d.setDate(diff));
}
```

- [ ] **Step 2: Create tier3 directory**

Run:
```bash
mkdir -p tests/tier3
```

- [ ] **Step 3: Commit**

```bash
git add tests/tier3/progress-tracking.spec.ts
git commit -m "test: add tier3 progress tracking tests"
```

---

## Task 21: Tier 3 - Profile Management Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier3/profile-management.spec.ts`

- [ ] **Step 1: Create profile-management.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Profile Management @tier3', () => {
  let api: ApiClient;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('GET /v1/user-profiles/tdee - gets TDEE calculation', async () => {
    const res = await api.get('/v1/user-profiles/tdee');

    expect(res.status).toBe(200);
    const body = await res.json() as { tdee: number; bmr: number; macros: unknown };
    expect(body.tdee).toBeGreaterThan(0);
    expect(body.bmr).toBeGreaterThan(0);
  });

  test('POST /v1/user-profiles/metrics - updates user metrics', async () => {
    const res = await api.post('/v1/user-profiles/metrics', {
      weight_kg: 72,
      activity_level: 'active'
    });

    expect(res.status).toBe(200);
    const body = await res.json() as { tdee: number };
    expect(body.tdee).toBeGreaterThan(0);
  });

  test('PUT /v1/user-profiles/custom-macros - sets custom macros', async () => {
    const res = await api.put('/v1/user-profiles/custom-macros', {
      calories: 2200,
      protein_g: 180,
      carbs_g: 220,
      fat_g: 70
    });

    expect(res.status).toBe(200);
  });

  test('PUT /v1/users/timezone - updates timezone', async () => {
    const res = await api.put('/v1/users/timezone', {
      timezone: 'America/Los_Angeles'
    });

    expect(res.status).toBe(200);
  });

  test('GET /v1/user-profiles/metrics - gets current metrics', async () => {
    const res = await api.get('/v1/user-profiles/metrics');

    expect(res.status).toBe(200);
    const body = await res.json() as { weight_kg: number; height_cm: number };
    expect(body.weight_kg).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier3/profile-management.spec.ts
git commit -m "test: add tier3 profile management tests"
```

---

## Task 22: Tier 3 - Referrals Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier3/referrals.spec.ts`

- [ ] **Step 1: Create referrals.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Referrals @tier3', () => {
  let api: ApiClient;
  let myReferralCode: string;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('GET /v1/referrals/my-code - gets or creates referral code', async () => {
    const res = await api.get('/v1/referrals/my-code');

    expect(res.status).toBe(200);
    const body = await res.json() as { code: string };
    expect(body.code).toBeTruthy();
    myReferralCode = body.code;
  });

  test('POST /v1/referrals/validate - validates a referral code', async () => {
    test.skip(!myReferralCode, 'No referral code available');

    const res = await api.post('/v1/referrals/validate', {
      code: myReferralCode
    });

    // Own code validation may return 400, other codes return 200
    expect([200, 400]).toContain(res.status);
  });

  test('GET /v1/referrals/stats - gets referral stats', async () => {
    const res = await api.get('/v1/referrals/stats');

    expect(res.status).toBe(200);
    const body = await res.json() as { 
      wallet_balance: number; 
      total_earned: number;
      conversions: number 
    };
    expect(body.wallet_balance).toBeGreaterThanOrEqual(0);
    expect(body.total_earned).toBeGreaterThanOrEqual(0);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier3/referrals.spec.ts
git commit -m "test: add tier3 referrals tests"
```

---

## Task 23: Tier 3 - Saved Suggestions Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier3/saved-suggestions.spec.ts`

- [ ] **Step 1: Create saved-suggestions.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Saved Suggestions @tier3', () => {
  let api: ApiClient;
  let savedSuggestionId: string;
  const e2eRunId = crypto.randomUUID();

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('POST /v1/saved-suggestions - bookmarks a suggestion', async () => {
    const res = await api.post('/v1/saved-suggestions', {
      suggestion: {
        id: crypto.randomUUID(),
        name: 'E2E Test Saved Meal',
        description: 'A test meal for E2E',
        nutrition: { calories: 500, protein_g: 30, carbs_g: 50, fat_g: 20 }
      }
    });

    expect(res.status).toBe(201);
    const body = await res.json() as { id: string };
    expect(body.id).toBeTruthy();
    savedSuggestionId = body.id;
  });

  test('GET /v1/saved-suggestions - lists saved suggestions', async () => {
    const res = await api.get('/v1/saved-suggestions');

    expect(res.status).toBe(200);
    const body = await res.json() as { suggestions: unknown[] };
    expect(Array.isArray(body.suggestions)).toBe(true);
  });

  test('DELETE /v1/saved-suggestions/{id} - removes bookmark', async () => {
    test.skip(!savedSuggestionId, 'No saved suggestion to delete');

    const res = await api.delete(`/v1/saved-suggestions/${savedSuggestionId}`);

    expect(res.status).toBe(200);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier3/saved-suggestions.spec.ts
git commit -m "test: add tier3 saved suggestions tests"
```

---

## Task 24: Tier 3 - Cheat Days Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier3/cheat-days.spec.ts`

- [ ] **Step 1: Create cheat-days.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';

test.describe('Cheat Days @tier3', () => {
  let api: ApiClient;
  const e2eRunId = crypto.randomUUID();
  const testDate = new Date().toISOString().split('T')[0];

  test.beforeAll(async () => {
    const env = readEnv();
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: env.e2eUid
    });
    api = await createApiClient({ baseUrl: env.baseUrl, idToken, e2eRunId });
  });

  test('POST /v1/cheat-days - marks a cheat day', async () => {
    const res = await api.post(`/v1/cheat-days?date=${testDate}`, {});

    expect(res.status).toBe(201);
  });

  test('GET /v1/cheat-days - gets cheat days for week', async () => {
    const res = await api.get(`/v1/cheat-days?week_of=${testDate}`);

    expect(res.status).toBe(200);
    const body = await res.json() as { cheat_days: string[] };
    expect(Array.isArray(body.cheat_days)).toBe(true);
  });

  test('DELETE /v1/cheat-days/{date} - unmarks cheat day', async () => {
    const res = await api.delete(`/v1/cheat-days/${testDate}`);

    expect(res.status).toBe(200);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier3/cheat-days.spec.ts
git commit -m "test: add tier3 cheat days tests"
```

---

## Task 25: Tier 3 - Account Deletion Tests

**Files:**
- Create: `mealtrack-e2e/tests/tier3/account-deletion.spec.ts`

- [ ] **Step 1: Create account-deletion.spec.ts**

```typescript
import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { readEnv } from '../../src/config.js';
import { getFirebaseIdToken } from '../../src/auth/firebase.js';
import { createApiClient, ApiClient } from '../../src/http/client.js';
import { seedTestData } from '../../src/db/seed.js';

test.describe('Account Deletion @tier3', () => {
  // Use a separate test user for deletion to avoid breaking other tests
  const deletionTestUid = `e2e-deletion-test-${crypto.randomUUID()}`;
  
  test('DELETE /v1/users/firebase/{uid} - deletes user account', async () => {
    const env = readEnv();

    // Seed a separate user for deletion
    await seedTestData(env.databaseUrl, deletionTestUid);

    // Get token for this user
    const idToken = await getFirebaseIdToken({
      firebaseServiceAccountJson: env.firebaseServiceAccountJson,
      firebaseWebApiKey: env.firebaseWebApiKey,
      uid: deletionTestUid
    });

    const api = await createApiClient({ 
      baseUrl: env.baseUrl, 
      idToken, 
      e2eRunId: crypto.randomUUID() 
    });

    // First sync the user
    await api.post('/v1/users/sync', {
      firebase_uid: deletionTestUid,
      email: `${deletionTestUid}@e2e-test.local`,
      provider: 'custom'
    });

    // Now delete
    const res = await api.delete(`/v1/users/firebase/${deletionTestUid}`);

    expect(res.status).toBe(200);
    const body = await res.json() as { deleted: boolean };
    expect(body.deleted).toBe(true);
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add tests/tier3/account-deletion.spec.ts
git commit -m "test: add tier3 account deletion test"
```

---

## Task 26: E2E Repo - GitHub Actions Workflow

**Files:**
- Create: `mealtrack-e2e/.github/workflows/e2e.yml`

- [ ] **Step 1: Create e2e.yml**

```yaml
name: E2E Tests

on:
  repository_dispatch:
    types: [run-e2e]
  workflow_dispatch:
  schedule:
    - cron: '0 6 * * *'

jobs:
  e2e:
    name: e2e
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Install Doppler CLI
        run: curl -Ls https://cli.doppler.com/install.sh | sh

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Cleanup test database
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          doppler run --project mealtrack-e2e --config ci -- \
            npx ts-node --esm src/db/cleanup.ts

      - name: Seed test data
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          doppler run --project mealtrack-e2e --config ci -- \
            npx ts-node --esm src/db/seed.ts

      - name: Run E2E tests
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
          E2E_CONFIRM_STAGING: '1'
        run: |
          doppler run --project mealtrack-e2e --config ci -- \
            npx playwright test --reporter=github,html

      - name: Upload test report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7

      - name: Cleanup test database
        if: always()
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          doppler run --project mealtrack-e2e --config ci -- \
            npx ts-node --esm src/db/cleanup.ts
```

- [ ] **Step 2: Create workflow directory**

Run:
```bash
mkdir -p .github/workflows
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/e2e.yml
git commit -m "ci: add E2E test workflow with Doppler and tier execution"
```

---

## Task 27: Final Integration Test

- [ ] **Step 1: Run tests locally to verify setup**

Run:
```bash
cd /Users/alexnguyen/Desktop/Nut/mealtrack-e2e
npm run db:cleanup
npm run db:seed
npx playwright test --project=tier1 --reporter=list
```

Expected: Tests execute (may have failures due to missing secrets locally)

- [ ] **Step 2: Commit all remaining changes**

```bash
git add -A
git commit -m "test: complete E2E integration test suite setup"
```

---

## Setup Checklist (Manual Steps)

### Doppler Setup
1. Create Doppler account at https://doppler.com
2. Create project `mealtrack-e2e`
3. Create config `ci`
4. Add secrets:
   - `E2E_BASE_URL` = `https://mealtrack-backend-main.onrender.com`
   - `DATABASE_URL` = Neon test branch connection string
   - `FIREBASE_WEB_API_KEY` = Firebase project API key
   - `FIREBASE_SERVICE_ACCOUNT_JSON` = Service account JSON (single line)
   - `E2E_UID` = Test user Firebase UID
   - `REVENUECAT_WEBHOOK_SECRET` = RevenueCat webhook secret
5. Generate service token and save as `DOPPLER_TOKEN`

### GitHub Setup (Backend Repo)
1. Go to Settings → Environments → Create `production`
2. Add required reviewers for `production` environment
3. Go to Settings → Secrets → Actions
4. Add `E2E_REPO_PAT` (Personal Access Token with `repo` scope)

### GitHub Setup (E2E Repo)
1. Go to Settings → Secrets → Actions
2. Add `DOPPLER_TOKEN` from Doppler service token

### Firebase Setup
1. Create test user in Firebase Console (or use existing)
2. Note the UID and add to Doppler as `E2E_UID`
3. Download service account JSON and add to Doppler

### Neon Setup
1. Create a test branch from your main database
2. Get connection string and add to Doppler as `DATABASE_URL`
