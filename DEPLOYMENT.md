# Railway Deployment Guide

## Overview
This application is configured for automatic deployment to Railway using GitHub integration.

## Deployment Method
- **Auto-deploy**: Pushes to `main` branch trigger automatic deployments
- **Builder**: Nixpacks (automatic Python detection)
- **Python Version**: 3.11 (specified in `.python-version`)

## Key Files

### `railway.json`
Main deployment configuration:
- Specifies Nixpacks as builder
- Configures Python 3.11 runtime
- Sets startup command
- Defines health check endpoint
- Configures restart policy

### `scripts/railway_start.py`
Production startup script that:
1. Runs database migrations (non-blocking on failure)
2. Starts FastAPI with uvicorn
3. Uses uvloop for better async performance
4. Configures workers based on WEB_CONCURRENCY env var

### `.python-version`
Ensures Railway uses Python 3.11 instead of default 3.7

## Environment Variables Required

Set these in Railway dashboard:

```bash
# Database
DATABASE_URL=mysql://user:password@host:port/database

# AI Services
GOOGLE_API_KEY=your-google-api-key

# Storage
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Optional Performance Tuning
WEB_CONCURRENCY=1  # Number of workers (default: 1)
PORT=8000          # Port (Railway sets this automatically)
```

## Deployment Flow

1. Push code to `main` branch
2. Railway detects changes and triggers build
3. Nixpacks builds Python 3.11 environment
4. Dependencies installed from `requirements.txt`
5. `scripts/railway_start.py` runs:
   - Database migrations execute
   - FastAPI app starts with uvicorn

## Monitoring

- Health check: `GET /health`
- API docs: `GET /docs`
- Logs: Available in Railway dashboard

## CI/CD Pipeline

- **Pull Requests**: GitHub Actions runs tests (`.github/workflows/ci.yml`)
- **Main Branch**: Railway auto-deploys after merge

## Best Practices Implemented

✅ Automatic deployments from GitHub
✅ Health checks for zero-downtime deployments
✅ Database migrations run before app start
✅ Proper Python version specification
✅ Production-ready uvicorn configuration
✅ Error handling and logging
✅ CI testing on pull requests
✅ No redundant configuration files

## Troubleshooting

1. **Migration Failures**: App continues running; check logs and fix in next deployment
2. **Port Issues**: Railway automatically sets PORT env var
3. **Memory Issues**: Adjust WEB_CONCURRENCY in Railway dashboard

## Updates

To update deployment configuration:
1. Modify `railway.json` or `scripts/railway_start.py`
2. Push to main branch
3. Railway automatically redeploys