# Testing & QA

## Standards
- **Framework**: `pytest` with `pytest-asyncio`.
- **Target Coverage**: 70%+ overall.
- **AAA Pattern**: Arrange, Act, Assert.

## Test Types
- **Unit**: Mock all dependencies, test one logic unit (`tests/unit/`).
- **Integration**: Test API endpoints or infrastructure with real/mocked external services (`tests/integration/`).

## Pinecone Testing
- Pinecone unit tests MUST mock the Inference API.
- Vectors in mocks MUST be 1024-dimensional.
- Integration tests should skip automatically if `PINECONE_API_KEY` is missing.
