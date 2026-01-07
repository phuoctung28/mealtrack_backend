# Database & API Conventions

## Database (SQLAlchemy)
- **Model Naming**: `DBMeal`, `DBNutrition` (Prefix with DB).
- **Primary Keys**: UUID strings (`id = Column(String(36), primary_key=True)`).
- **Timestamps**: Always include `created_at` and `updated_at`.
- **Unit of Work**: Use the UoW pattern via `AsyncSession`.

## API (FastAPI)
- **Versioning**: All routes under `/v1/`.
- **Schemas**: Separate `Request` and `Response` Pydantic models.
- **Mappers**: Use explicit mappers to convert between Domain entities and API Schemas.
- **REST**: Follow standard HTTP methods (GET, POST, PUT, DELETE).
