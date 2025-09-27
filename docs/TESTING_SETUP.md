# Testing Setup Guide

## Overview

The MealTrack application uses MySQL for both development and testing to ensure consistency between test and production environments.

## GitHub Actions CI Setup

### MySQL Service Container

The CI pipeline uses a Docker service container for MySQL testing:

```yaml
services:
  mysql:
    image: mysql:8.0
    env:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: mealtrack_test
      MYSQL_USER: test_user
      MYSQL_PASSWORD: test_password
    ports:
      - 3306:3306
    options: >-
      --health-cmd="mysqladmin ping"
      --health-interval=10s
      --health-timeout=5s
      --health-retries=5
```

### How Service Containers Work

1. **Automatic Startup**: GitHub Actions starts the MySQL container before running the job
2. **Network Access**: The container is accessible at `localhost:3306` from the runner
3. **Health Checks**: The `--health-cmd` ensures MySQL is ready before tests run
4. **Isolation**: Each workflow run gets a fresh MySQL instance
5. **Cleanup**: The container is automatically removed after the job completes

### Test Database Connection

When `CI=true` is set, the test configuration automatically uses:
- Host: `localhost`
- Port: `3306`
- User: `test_user`
- Password: `test_password`
- Database: `mealtrack_test`

## Local Testing Setup

### 1. Install MySQL

```bash
# macOS
brew install mysql
brew services start mysql

# Ubuntu/Debian
sudo apt-get install mysql-server
sudo systemctl start mysql
```

### 2. Create Test Database

```bash
# Run the setup script
python scripts/setup_test_db.py

# Or manually:
mysql -u root -p
CREATE DATABASE mealtrack_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Configure Environment

Create a `.env.dev` file:
```env
TEST_DB_HOST=localhost
TEST_DB_PORT=3306
TEST_DB_USER=root
TEST_DB_PASSWORD=your_password
TEST_DB_NAME=mealtrack_test
```

### 4. Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src

# Specific markers
pytest -m unit
pytest -m integration
```

## Test Database Isolation

### Transaction Rollback

Each test runs in a database transaction that's rolled back after the test:

```python
@pytest.fixture(scope="function")
def test_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
```

This ensures:
- No test data persists between tests
- Tests can't interfere with each other
- Database state is predictable

### Benefits of Using MySQL for Tests

1. **Consistency**: Same database engine as production
2. **Feature Parity**: All MySQL features available in tests
3. **Real Constraints**: Foreign keys, unique constraints work as expected
4. **Performance**: With transaction rollback, tests remain fast
5. **CI Integration**: Docker service containers make setup easy

## Troubleshooting

### pytest-asyncio Error

If you see `AttributeError: 'Package' object has no attribute 'obj'`:
- Ensure `pytest-asyncio==0.21.1` is installed
- Check `asyncio_mode = auto` in pytest.ini

### MySQL Connection Error

If tests can't connect to MySQL:
1. Check MySQL is running: `mysqladmin ping`
2. Verify credentials: `mysql -u test_user -p`
3. Check database exists: `SHOW DATABASES;`

### CI MySQL Not Ready

The CI includes a wait step:
```bash
until mysqladmin ping -h"localhost" -P"3306" --silent; do
  echo 'Waiting for MySQL...'
  sleep 2
done
```

This ensures MySQL is fully ready before tests run.

## Best Practices

1. **Use Fixtures**: Create test data using fixtures, not direct SQL
2. **Mock External Services**: Use mocks for APIs, storage, etc.
3. **Test Isolation**: Each test should be independent
4. **Fast Tests**: Keep unit tests fast, integration tests thorough
5. **CI/CD**: All tests must pass before merging