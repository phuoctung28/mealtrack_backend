# Seeding Meal Images Locally

This guide explains how to add meal names to the resolver queue and run the image resolver on your local machine.

---

## How it works

```
seed_meal_images.py
      │
      ▼
pending_meal_image_resolution   ← queue table (Neon Postgres)
      │
      ▼
resolve_pending_images.py       ← drain script (also runs as nightly cron)
      │
      ├─ candidate_image_url present?
      │     YES → download + CLIP-validate (threshold 0.85)
      │     NO  → web search via FoodImageSearchService → download + validate
      │
      ├─ passes validation? → upload to Cloudinary → store in meal_image_cache
      └─ fails validation?  → Pollinations.ai → fallback Imagen → store as ai_generated
```

---

## Prerequisites

**1. Python dependencies**

```bash
pip install -r requirements.txt
```

`sentence-transformers` and `torch` are included — CLIP will be downloaded on first run (~400 MB, cached to `~/.cache/huggingface`).

**2. Environment variables**

Create or update `.env` in the project root:

```dotenv
# Required for all scripts
NEON_DATABASE_URL=postgresql://user:pass@host/db   # or DATABASE_URL

# Required only for resolve_pending_images.py
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

# Optional — AI fallback generators
GOOGLE_API_KEY=...                    # Imagen fallback
POLLINATIONS_BASE_URL=https://image.pollinations.ai/prompt

# Tune behaviour
IMAGE_MATCH_THRESHOLD=0.85            # CLIP cosine threshold (0–1)
MAX_JOBS_PER_CRON=50                  # items to process per drain run
CRON_EXTERNAL_CALL_DELAY_SECONDS=2.0  # delay between items
```

> **Neon note:** The connection string must include `sslmode=require`.
> Example: `postgresql://alex:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

---

## Step 1 — Seed meal names into the queue

### Option A: CSV file

Edit `scripts/data/meal_images_seed.csv`:

```csv
meal_name,image_url,thumbnail_url,source
Pho Bo,,,
Banh Mi,https://images.pexels.com/photos/1234/banh-mi.jpg,,pexels
Com Tam,,,
```

- **`meal_name`** — required. Vietnamese or English, any casing.
- **`image_url`** — optional. If you already have a URL, supply it here. The resolver will validate it with CLIP and skip the web-search step.
- **`thumbnail_url`** — optional. Smaller preview URL (used in the API response).
- **`source`** — optional label, e.g. `pexels`, `unsplash`, `manual`.

Run:

```bash
python scripts/seed_meal_images.py --csv scripts/data/meal_images_seed.csv
```

### Option B: Inline names

```bash
python scripts/seed_meal_images.py --meals "Pho Bo" "Banh Mi" "Com Tam"
```

### Dry-run (preview without writing)

```bash
python scripts/seed_meal_images.py --csv scripts/data/meal_images_seed.csv --dry-run
```

Output:

```
INFO DRY RUN — would enqueue 5 item(s):
INFO   Pho Bo                                    image=(none)
INFO   Banh Mi                                   image=https://...
...
```

---

## Step 2 — Run the resolver locally

```bash
python scripts/resolve_pending_images.py
```

This drains up to `MAX_JOBS_PER_CRON` (default 50) items from the queue, resolves each one, and prints a summary:

```
INFO drain: 5 items to process
INFO drain summary: {'processed': 4, 'matched': 3, 'ai_generated': 1, 'failed': 1, 'skipped': 0}
```

**`matched`** — a candidate or web-search image passed CLIP validation  
**`ai_generated`** — no image passed; Pollinations/Imagen was used  
**`failed`** — all generators failed; item stays in queue for retry  
**`skipped`** — item exceeded `MAX_RESOLUTION_ATTEMPTS` (default 5)

---

## Step 3 — Verify the results

Query the cache table directly:

```sql
SELECT meal_name, source, confidence, image_url
FROM meal_image_cache
ORDER BY created_at DESC
LIMIT 20;
```

Or check what's still pending:

```sql
SELECT meal_name, attempts, last_error
FROM pending_meal_image_resolution
ORDER BY enqueued_at ASC;
```

---

## Re-running / overwriting

The seed script uses `ON CONFLICT (name_slug) DO NOTHING` — duplicate meal names are silently skipped. If you want to force a re-resolve for a meal that's already cached, delete its row first:

```sql
DELETE FROM meal_image_cache WHERE name_slug = 'pho-bo';
DELETE FROM pending_meal_image_resolution WHERE name_slug = 'pho-bo';
```

Then re-seed and re-run the resolver.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `SSL connection is required` | Missing `sslmode=require` | Append `?sslmode=require` to the DB URL |
| `ModuleNotFoundError: sentence_transformers` | Missing deps | `pip install -r requirements.txt` |
| CLIP model downloads every run | HF cache missing | Set `TRANSFORMERS_CACHE=~/.cache/huggingface` in `.env` |
| All items fail with HTTP 429 | Pexels/Unsplash rate limit | Lower `MAX_JOBS_PER_CRON` or increase `CRON_EXTERNAL_CALL_DELAY_SECONDS` |
| `all image generators failed` | Pollinations/Imagen down | Check `GOOGLE_API_KEY`; Pollinations is free but occasionally flaky |
