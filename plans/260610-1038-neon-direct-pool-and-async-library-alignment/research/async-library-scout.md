---
type: research
topic: sync library audit for async runtime alignment
created: "2026-06-10"
---

# Async Library Scout

## Summary

Most active external HTTP adapters already use `httpx.AsyncClient`. Remaining
sync runtime concerns are concentrated in USDA FoodDataService and Cloudinary.

## Findings

### DB Drivers

- `asyncpg` is the runtime DB driver.
- `psycopg2-binary` remains migration-only through Alembic utilities.
- Do not remove `psycopg2-binary` in this plan.

### Redis

- `src/infra/cache/redis_client.py` uses `redis.asyncio`.
- No Redis library swap required for this plan.

### Already Async HTTP Adapters

- `open_food_facts_service.py`
- `fat_secret_service.py`
- `nutritionix_service.py`
- `brave_search_nutrition_service.py`
- `posthog_adapter.py`
- image generator/search adapters using `httpx.AsyncClient`

### Sync Runtime Candidates

- `src/infra/adapters/food_data_service.py`
  - Uses `requests.Session` inside async methods.
  - Best fix: convert to `httpx.AsyncClient` with injectable client/transport.

- `src/infra/adapters/cloudinary_image_store.py`
  - Uses sync Cloudinary SDK and `requests.get/head`.
  - There is no obvious first-party async Cloudinary SDK.
  - Best fix: add explicit async wrapper methods and migrate async runtime
    callers to await off-loop wrappers.

### Tests/Scripts

- Several tests patch `requests`.
- Some scripts/tests use sync SQLAlchemy engines.
- These are not automatically runtime problems; do not purge blindly.

## Design Conclusion

Do not make this a generic dependency purge. Convert native async candidates
first. Contain sync-only vendor SDK calls with explicit off-loop async wrappers.

## Open Questions

None.
