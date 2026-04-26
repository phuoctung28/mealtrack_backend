# Integration Test Suite Design

**Date:** 2026-04-26  
**Status:** Approved  
**Author:** Claude + Alex

## Overview

Pre-release integration test suite that runs as a CI gate on merge to main. Tests essential endpoints against real external services inside an isolated test container.

## Goals

- Verify core user journey and meal tracking flows work before release
- Run tests in isolated container environment
- Use real external services (Neon, Firebase, Gemini, Cloudinary)
- Require manual approval before building production image

## Pipeline Flow

```
merge to main
     ↓
Build Test Container (Dockerfile.test)
     ↓
Run Unit Tests (in container)
     ↓
Run Integration Tests (in container, with Doppler secrets)
     ↓
Manual Approval (GitHub environment gate)
     ↓
Build & Push Production Image (ghcr.io)
```

## Test Scope

### Core User Journey (`test_user_journey.py`)

| Order | Test | Endpoint |
|-------|------|----------|
| 1 | `test_user_sync` | `POST /v1/users/sync` |
| 2 | `test_user_onboarding` | `POST /v1/users/onboarding` |
| 3 | `test_get_profile` | `GET /v1/user-profiles/me` |
| 4 | `test_update_profile` | `PUT /v1/user-profiles/me` |
| 5 | `test_delete_account` | `DELETE /v1/users/me` |

### Meal Tracking Flow (`test_meal_tracking.py`)

| Order | Test | Endpoint |
|-------|------|----------|
| 1 | `test_meal_image_analyze` | `POST /v1/meals/image/analyze` |
| 2 | `test_get_meal` | `GET /v1/meals/{id}` |
| 3 | `test_update_meal` | `PUT /v1/meals/{id}` |
| 4 | `test_manual_meal_create` | `POST /v1/meals/manual` |
| 5 | `test_delete_meal` | `DELETE /v1/meals/{id}` |

## File Structure

```
tests/e2e/
├── conftest.py                    # Firebase token fetch, DB cleanup/seed
├── test_user_journey.py           # Core user flow tests
├── test_meal_tracking.py          # Meal tracking tests
├── fixtures/
│   └── test_meal_image.jpg        # Sample image for analyze endpoint
└── utils/
    ├── db_cleanup.py              # Cleanup functions for Neon
    ├── db_seed.py                 # Seed data population
    └── auth.py                    # Firebase token helper
```

## Test Container (Dockerfile.test)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-test.txt

COPY src/ ./src/
COPY tests/ ./tests/
COPY pytest.ini pyproject.toml alembic.ini ./
COPY migrations/ ./migrations/

CMD ["pytest", "tests/", "-v", "--tb=short"]
```

## Doppler Integration

**Project:** `mealtrack-backend`  
**Config:** `test`

**Secrets:**
- `DATABASE_URL` - Neon test branch connection string
- `FIREBASE_API_KEY` - Firebase project API key
- `TEST_USER_EMAIL` - Pre-created test user email
- `TEST_USER_PASSWORD` - Pre-created test user password
- `GOOGLE_API_KEY` - Gemini AI key
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

**scripts/run-e2e-tests.sh:**
```bash
#!/bin/bash
set -e

if ! command -v doppler &> /dev/null; then
  curl -Ls https://cli.doppler.com/install.sh | sh
fi

doppler run \
  --project mealtrack-backend \
  --config test \
  -- docker run --rm \
    -e DATABASE_URL \
    -e FIREBASE_API_KEY \
    -e TEST_USER_EMAIL \
    -e TEST_USER_PASSWORD \
    -e GOOGLE_API_KEY \
    -e CLOUDINARY_CLOUD_NAME \
    -e CLOUDINARY_API_KEY \
    -e CLOUDINARY_API_SECRET \
    mealtrack:test pytest tests/e2e -v
```

## GitHub Actions Workflow

**.github/workflows/release-pipeline.yml:**
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
      - run: docker run --rm ${{ env.TEST_IMAGE }} pytest tests/unit -v --cov=src --cov-fail-under=65

  integration-tests:
    name: Integration Tests
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: test-image
      - run: docker load -i test-image.tar
      - name: Install Doppler CLI
        run: curl -Ls https://cli.doppler.com/install.sh | sh
      - name: Run E2E Tests
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
        run: |
          doppler run --project mealtrack-backend --config test -- \
            docker run --rm \
              -e DATABASE_URL -e FIREBASE_API_KEY \
              -e TEST_USER_EMAIL -e TEST_USER_PASSWORD \
              -e GOOGLE_API_KEY \
              -e CLOUDINARY_CLOUD_NAME -e CLOUDINARY_API_KEY -e CLOUDINARY_API_SECRET \
              ${{ env.TEST_IMAGE }} \
              pytest tests/e2e -v

  approval:
    name: Manual Approval
    needs: integration-tests
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

## Data Management

**Strategy:** Full cleanup + populate at start of each run

**Workflow:**
1. `cleanup_db()` - Clear previous run's test data
2. `populate_seed_data()` - Create test user in DB, base data
3. Run tests
4. `cleanup_db()` - Clean after (optional)

## External Services

| Service | Usage | Authentication |
|---------|-------|----------------|
| Neon PostgreSQL | Shared test branch | Connection string in Doppler |
| Firebase Auth | Get bearer token for test user | API key + email/password in Doppler |
| Gemini AI | Real AI calls during meal analysis | API key in Doppler |
| Cloudinary | Real image storage | Credentials in Doppler |

## Firebase Token Acquisition

The `tests/e2e/utils/auth.py` helper obtains a fresh Firebase ID token at test session start:

```python
import httpx

def get_firebase_token(api_key: str, email: str, password: str) -> str:
    """Get Firebase ID token via REST API."""
    response = httpx.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
        json={"email": email, "password": password, "returnSecureToken": True}
    )
    response.raise_for_status()
    return response.json()["idToken"]
```

Token is cached in pytest fixture scope (`session`) so all tests reuse it.

## Required Setup

### GitHub
1. Create `production` environment with required reviewers
2. Add `DOPPLER_TOKEN` secret

### Doppler
1. Create project `mealtrack-backend`
2. Create config `test`
3. Add all secrets listed above
4. Generate service token for CI

### Firebase
1. Create test user (email/password)
2. Store credentials in Doppler

### Neon
1. Create dedicated test branch
2. Store connection string in Doppler

## Implementation Files

| File | Purpose |
|------|---------|
| `Dockerfile.test` | Test container with test deps |
| `.github/workflows/release-pipeline.yml` | CI pipeline |
| `scripts/run-e2e-tests.sh` | Local test runner with Doppler |
| `tests/e2e/conftest.py` | Shared fixtures, auth, cleanup |
| `tests/e2e/test_user_journey.py` | User flow tests |
| `tests/e2e/test_meal_tracking.py` | Meal flow tests |
| `tests/e2e/utils/db_cleanup.py` | DB cleanup functions |
| `tests/e2e/utils/db_seed.py` | Seed data functions |
| `tests/e2e/utils/auth.py` | Firebase token helper |
| `tests/e2e/fixtures/test_meal_image.jpg` | Test image |
