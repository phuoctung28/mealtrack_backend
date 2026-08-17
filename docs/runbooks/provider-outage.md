# Provider Outage Runbook

Use this when FatSecret, USDA FoodData Central, OpenAI, Cloudflare Workers AI, or
Redis has elevated errors or latency.

## First Checks

- Check `/health` and application 5xx rate.
- Check provider dashboards or status pages from the vendor console.
- Check recent deploys and env-var changes in Render.
- Check `food_search.requests` by `source` and `status`.
- Check `meal_catalog.snapshot.refresh` and `meal_catalog.snapshot.last_good`.

Never paste provider credentials into incident notes, Slack, tickets, or logs.
Credentials must stay in the configured secret manager or Render environment
settings.

## Expected Degraded Behavior

| Dependency | Expected behavior |
|---|---|
| Redis optional cache | Local-first food search treats cache errors as misses and continues. Required Redis-backed state, such as legacy meal suggestion sessions, may fail fast. |
| FatSecret search | `/v1/foods/search` returns verified local `food_reference` results when available. Provider enrichment may be absent. |
| USDA barcode/details | Barcode cascade skips unavailable providers and continues to the next configured source or editable estimate when safe. |
| OpenAI translation | Non-English search falls back to local/provider results without translated names. |
| Cloudflare Workers AI | AI manager uses configured fallback chain when available; catalog image generation can be paused. |

## Response Steps

1. Confirm the affected dependency and error class from logs or metrics.
2. Confirm local-first search still returns bounded results:

```bash
curl -fsS "$HOST/v1/foods/search?query=rice&limit=5&language=en" \
  -H "Authorization: Bearer $TOKEN"
```

3. If recommendations fail because catalog snapshot cannot load, stop exposing
   the recommendation entry point and restore the last known healthy app image if
   the issue began with a deploy.
4. If provider quota is exhausted, rotate only through approved provider account
   controls. Do not paste replacement credentials into ad hoc scripts.
5. When the provider recovers, run the same smoke request and confirm metrics
   return to normal for at least 10 minutes.

## Recovery Evidence

Record UTC start/end time, affected provider, error class, operator action,
dashboard link, and recovery duration. Do not record raw payloads, tokens,
search text, user IDs, or secrets.
