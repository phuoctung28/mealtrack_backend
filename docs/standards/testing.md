# Testing & QA

## Standards
- **Framework**: `pytest` with `pytest-asyncio`.
- **Target Coverage**: 70%+ overall.
- **AAA Pattern**: Arrange, Act, Assert.

## Test Types
- **Unit**: Mock all dependencies, test one logic unit (`tests/unit/`).
- **Integration**: Test API endpoints or infrastructure with real/mocked external services (`tests/integration/`).

## Food Search Testing
- Unit tests MUST mock external food lookup and embedding providers.
- Vector fixtures should preserve the production embedding dimensionality when behavior depends on shape.
- Integration tests that require external provider credentials should skip automatically when the relevant env vars are missing.
