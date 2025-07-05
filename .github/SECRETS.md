# GitHub Secrets Configuration

This document lists the secrets that need to be configured in your GitHub repository for the CI/CD pipeline to work properly.

## Required Secrets

The following secrets should be added to your repository settings (Settings → Secrets and variables → Actions):

### Optional Secrets (for integration tests with real services)

1. **OPENAI_API_KEY**
   - Description: OpenAI API key for vision analysis
   - Required: No (tests use mocks by default)
   - Example: `sk-...`

2. **CLOUDINARY_CLOUD_NAME**
   - Description: Cloudinary cloud name
   - Required: No (tests use mock storage by default)
   - Example: `your-cloud-name`

3. **CLOUDINARY_API_KEY**
   - Description: Cloudinary API key
   - Required: No (tests use mock storage by default)
   - Example: `123456789012345`

4. **CLOUDINARY_API_SECRET**
   - Description: Cloudinary API secret
   - Required: No (tests use mock storage by default)
   - Example: `your-api-secret`

## Environment Variables Set by CI

The following environment variables are automatically set by the CI pipeline:

- `TESTING=true` - Indicates tests are running
- `PYTHONPATH=.` - Ensures proper module imports
- `USE_MOCK_STORAGE=1` - Uses mock storage instead of Cloudinary
- `USE_MOCK_VISION_SERVICE=1` - Uses mock vision service instead of real AI

## Notes

1. All tests use SQLite in-memory database, so no MySQL configuration is needed
2. Mock services are used by default to ensure tests can run without external dependencies
3. If you want to run integration tests with real services, add the appropriate secrets
4. The CI will use mock values if secrets are not configured, allowing tests to pass