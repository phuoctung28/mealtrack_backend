# Database & API Conventions

## Database Design Rules

These rules are mandatory for new tables, migrations, and schema refactors.
Use the architecture review in `plans/reports/260609-0955-database-model-architecture-review.md`
as the current normalization roadmap.

### Source of Truth

- PostgreSQL/Neon is the canonical database engine.
- SQLAlchemy ORM models and Alembic migrations must describe the same schema.
- Alembic migrations are the production schema authority. Do not rely on
  `Base.metadata.create_all()` for production schema creation.
- Every ORM model must be imported by the central model registry so
  `Base.metadata` and Alembic autogenerate see the full schema.

### Normalization

- OLTP source-of-truth tables must follow 3NF unless an exception is explicitly
  documented in the model and migration notes.
- Business entities, user preferences, workflow state, and queryable product data
  must be stored in typed columns or child/reference tables, not only JSON.
- JSON is allowed only for:
  - raw external provider snapshots for audit/debugging,
  - rebuildable cache/read-model payloads,
  - immutable append-only context where individual fields are not queried.
- Existing JSON source-of-truth fields must be normalized with
  expand-migrate-contract rollout:
  1. add normalized tables/columns,
  2. backfill existing rows idempotently,
  3. dual-write old and new shapes,
  4. switch reads to normalized tables with fallback,
  5. retire old JSON fields in a later migration.

### Ownership and Relationships

- Every user-owned table must have `ForeignKey("users.id")` unless there is a
  documented retention/legal reason not to.
- Choose `ondelete` intentionally:
  - `CASCADE` for private user-owned logs/preferences that should disappear on
    account deletion,
  - `SET NULL`, anonymization, or restricted deletion for accounting/audit data.
- Foreign keys should be indexed through a compound query index when possible.
- Many-to-many or repeated values must use join tables. Do not store arrays as
  the only source of truth for preferences, allergies, tags, recipe steps, or
  similar repeated business values.

### Keys, Names, and Timestamps

- Use explicit table names in snake_case.
- Use established local model naming. Current ORM classes use names like
  `User`, `UserProfile`, `MealORM`, and `SavedSuggestionModel`; do not introduce
  a new `DB*` naming convention.
- Top-level aggregate IDs use UUID strings unless there is a proven reason for
  another key type.
- Child rows may use integer IDs when they are never exposed as stable API IDs.
- All mutable business tables must include `created_at` and `updated_at`.
- Time columns that represent events must be timezone-aware and stored as UTC.

### Migration Safety

- New migrations must chain from the current Alembic head and preserve a single
  head. Verify with `alembic heads`.
- Prefer timestamped migration IDs already used by this repo.
- Backfills must be idempotent: safe to retry after partial deploy failure.
- Data migrations must handle nulls, malformed legacy JSON, missing referenced
  users, and duplicate records deterministically.
- Do not drop legacy columns in the same release that introduces replacement
  columns/tables. Keep compatibility until reads and writes have migrated.
- Add constraints in stages when needed:
  1. create nullable columns/tables,
  2. backfill,
  3. validate data,
  4. add `NOT NULL`, `UNIQUE`, `CHECK`, and FK constraints.
- Migration downgrade paths must not silently destroy user data unless the
  migration is explicitly irreversible and documented as such.

### Backward Compatibility

- API request/response shapes must remain compatible during schema migration.
- Mappers/repositories own compatibility reads:
  - read normalized data first,
  - fall back to old JSON/legacy columns while rollout is in progress.
- Write paths must dual-write when old clients or old read paths still exist.
- Mobile must keep receiving backend-derived calorie values. Never move calorie
  derivation to the client.
- Feature flags or config guards are recommended for large read-cutovers.

### Query and Index Rules

- Index for real query patterns, not every column.
- Prefer compound indexes matching filter/order patterns, for example
  `(user_id, logged_at)` for per-user timeline reads.
- Use partial indexes for hot status filters when Postgres can use them.
- Avoid duplicate single-column indexes that are covered by compound indexes.
- Add `EXPLAIN` evidence before adding heavyweight indexes to high-write tables.

### Transaction and Repository Rules

- Request-path DB work should use `AsyncUnitOfWork` and async repositories.
- Repositories used inside `AsyncUnitOfWork` must not call `commit()`.
- Sync UoW/repositories are acceptable for cron or isolated scripts, but do not
  introduce new sync DB work in async request paths without an explicit reason.
- Keep mapping between ORM and domain/API models explicit. Do not leak ORM models
  directly through API responses.

### New Table Checklist

Before creating a table, answer yes to all applicable checks:

- Does it have a clear owner aggregate or documented standalone reason?
- If user-owned, does it have a FK to `users.id`?
- Is repeated/queryable data normalized into child/reference tables?
- Are JSON fields only snapshots/cache/audit/temporary compatibility fields?
- Are timestamps and timezone semantics explicit?
- Are uniqueness and status invariants enforced by DB constraints where possible?
- Are indexes based on actual read paths?
- Is the migration backward compatible with old rows and old app versions?
- Is the ORM model imported by the central model registry?
- Are mapper/repository tests updated for both legacy and normalized data during rollout?

## API (FastAPI)
- **Versioning**: All routes under `/v1/`.
- **Schemas**: Separate `Request` and `Response` Pydantic models.
- **Mappers**: Use explicit mappers to convert between Domain entities and API Schemas.
- **REST**: Follow standard HTTP methods (GET, POST, PUT, DELETE).

---

## Meal Suggestions API

### Endpoints

| Method | Endpoint | Purpose | Phase |
|--------|----------|---------|-------|
| POST | `/v1/meal-suggestions/discover` | Discover meal suggestions for a user context | Current |
| POST | `/v1/meal-suggestions/recipes` | Generate recipes for selected suggestions | Current |
| POST | `/v1/meal-suggestions/save` | Save a generated suggestion | Current |

### Request Schemas

```python
class DiscoverMealsRequest(BaseModel): ...
class GenerateRecipesRequest(BaseModel): ...
class SaveMealSuggestionRequest(BaseModel): ...
```

### Language Support (Phase 01)

- **Supported Languages**: English (en), Vietnamese (vi), Spanish (es), French (fr), German (de), Japanese (ja), Mandarin (zh)
- **Default**: English (en)
- **Validation**: Invalid codes fallback to 'en' with warning
- **Field Location**: request schema language field where supported by the current route
- **Scope**: Meal names, descriptions, and cooking instructions

### Example Request (with language)

```json
POST /v1/meal-suggestions/discover
{
  "meal_type": "lunch",
  "meal_portion_type": "main",
  "ingredients": ["chicken breast", "broccoli", "rice"],
  "cooking_time_minutes": 30,
  "language": "vi",
  "dietary_preferences": []
}
```

### Response Structure

The current API returns route-specific suggestion payloads with multilingual names, descriptions, and instructions where generated by the recipe flow.
