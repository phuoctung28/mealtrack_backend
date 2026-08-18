-- Backfill meal_catalog.popularity_rank on SIT/Neon without re-importing seeds.
--
-- Why: GET /v1/meal-catalog (feed=popular) returns 503 when any active meal
-- has popularity_rank IS NULL. The 20260816000005 migration added the column
-- as nullable and did not populate it.
--
-- Safe: only fills NULL ranks. Existing curated ranks are left unchanged.
-- New ranks continue after MAX(popularity_rank) so they do not collide.
-- Lower rank sorts first (1 is shown before 2).
--
-- After applying: wait up to 5 minutes for the in-process catalog snapshot
-- TTL, or restart the SIT web service so ranks are loaded.
--
-- Run in the Neon SQL Editor against the SIT database (neondb).

-- 1) Current coverage
SELECT
    count(*) AS total,
    count(*) FILTER (WHERE is_active) AS active,
    count(*) FILTER (WHERE is_active AND popularity_rank IS NOT NULL)
        AS active_ranked,
    count(*) FILTER (WHERE is_active AND popularity_rank IS NULL)
        AS active_unranked,
    count(*) FILTER (WHERE popularity_rank IS NULL) AS all_unranked
FROM meal_catalog;

-- 2) Preview assignment (no writes)
WITH bounds AS (
    SELECT coalesce(max(popularity_rank), 0) AS max_rank
    FROM meal_catalog
),
ranked AS (
    SELECT
        mc.id,
        mc.catalog_key,
        mc.name,
        mc.cuisine,
        mc.is_active,
        mc.popularity_rank AS current_rank,
        bounds.max_rank
        + row_number() OVER (
            ORDER BY mc.cuisine ASC, mc.name ASC, mc.id ASC
        ) AS proposed_rank
    FROM meal_catalog AS mc
    CROSS JOIN bounds
    WHERE mc.popularity_rank IS NULL
)
SELECT *
FROM ranked
ORDER BY proposed_rank;

-- 3) Apply
BEGIN;

WITH bounds AS (
    SELECT coalesce(max(popularity_rank), 0) AS max_rank
    FROM meal_catalog
),
ranked AS (
    SELECT
        mc.id,
        bounds.max_rank
        + row_number() OVER (
            ORDER BY mc.cuisine ASC, mc.name ASC, mc.id ASC
        ) AS new_rank
    FROM meal_catalog AS mc
    CROSS JOIN bounds
    WHERE mc.popularity_rank IS NULL
)
UPDATE meal_catalog AS mc
SET
    popularity_rank = ranked.new_rank,
    updated_at = now()
FROM ranked
WHERE mc.id = ranked.id;

-- 4) Confirm popular feed can serve
SELECT
    count(*) AS total,
    count(*) FILTER (WHERE is_active) AS active,
    count(*) FILTER (WHERE is_active AND popularity_rank IS NOT NULL)
        AS active_ranked,
    count(*) FILTER (WHERE is_active AND popularity_rank IS NULL)
        AS active_unranked
FROM meal_catalog;

-- Must be 0 for GET /v1/meal-catalog?feed=popular to stop 503-ing.
SELECT count(*) AS active_unranked
FROM meal_catalog
WHERE is_active AND popularity_rank IS NULL;

COMMIT;
