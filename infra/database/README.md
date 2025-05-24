# Database Implementation

This directory contains the ORM implementation for the MealTrack backend.

## Components

- `config.py` - Database connection configuration
- `models/` - SQLAlchemy model definitions
- `init_db.py` - Script to initialize the database tables

## Setup

1. Install MySQL server on your local machine or use Docker:

```bash
docker run --name mealtrack-mysql -e MYSQL_ROOT_PASSWORD=rootpassword -e MYSQL_DATABASE=mealtrack -p 3306:3306 -d mysql:8.0
```

2. Create a `.env` file at the project root with the following settings:

```
DB_USER=root
DB_PASSWORD=rootpassword
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mealtrack
```

3. Run the database setup script:

```bash
python scripts/setup_db.py
```

4. Initialize the database schema:

```bash
python -m infra.database.init_db
```

## Migrations with Alembic

The project uses Alembic for database migrations.

### Create a new migration

```bash
alembic revision --autogenerate -m "Initial migration"
```

### Run migrations

```bash
alembic upgrade head
```

### Rollback migrations

```bash
alembic downgrade -1
``` 