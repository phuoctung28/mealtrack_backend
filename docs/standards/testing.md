# Testing & QA

## Standards
- **Framework**: `pytest` with `pytest-asyncio`.
- **Target Coverage**: 70%+ overall.
- **AAA Pattern**: Arrange, Act, Assert.

## Test Types
- **Unit**: Mock all dependencies, test one logic unit (`tests/unit/`).
- **Integration**: Test API endpoints or infrastructure with real/mocked external services (`tests/integration/`).

## Vector Cache Testing
- Test active nearest-neighbor behavior against the PostgreSQL `pgvector`
  adapter or a narrow port fake.
- Keep Pinecone references only in historical migration tests; Pinecone is not
  registered in the current runtime.
