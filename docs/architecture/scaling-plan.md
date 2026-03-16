# Scaling Plan: Multi-Service Architecture with Distributed Job Queue

**Created:** March 13, 2026
**Status:** Proposal
**Target:** 10,000 DAU / 5,000 concurrent AI requests
**Platform:** Northflank

---

## Table of Contents

1. [Current Limitations](#1-current-limitations)
2. [Target Architecture](#2-target-architecture)
3. [Service Topology on Northflank](#3-service-topology-on-northflank)
4. [Distributed Job Queue Design](#4-distributed-job-queue-design)
5. [Migration Path](#5-migration-path)
6. [Caching Improvements](#6-caching-improvements)
7. [Image Pipeline Optimization](#7-image-pipeline-optimization)
8. [AI Cost & Throughput Optimization](#8-ai-cost--throughput-optimization)
9. [Observability & Reliability](#9-observability--reliability)
10. [Cost Projections](#10-cost-projections)
11. [Queue Provider Switching](#11-queue-provider-switching-upstash--dedicated)

---

## 1. Current Limitations

### 1.1 In-Memory Event Bus Cannot Cross Service Boundaries

The `PyMediatorEventBus` is a process-local singleton. Handlers and subscribers
exist only in the memory of the process that created them:

```python
# src/api/dependencies/event_bus.py
_configured_event_bus: Optional[EventBus] = None   # module-level singleton

def get_configured_event_bus() -> EventBus:
    global _configured_event_bus
    if _configured_event_bus is not None:
        return _configured_event_bus
    ...
```

Domain events published via `asyncio.create_task()` run in the same event loop
as the API request. A separate worker service would never receive them.

**Impact:**

- Cannot offload AI-heavy work to a separate process/service.
- Scaling horizontally (multiple API replicas) is safe for `send()` (each
  replica handles its own commands/queries), but `publish()` events only reach
  subscribers within the same process.
- Under high AI load, long-running Gemini calls (3-10s) block the API event
  loop, degrading response times for all endpoints.

### 1.2 Synchronous AI in Request Path

`UploadMealImageImmediatelyHandler.handle()` performs the full pipeline inline:

```
HTTP request → upload image → call Gemini → parse → translate → save → respond
```

At 5s average Gemini latency, 100 concurrent image uploads = 100 connections
held open for 5+ seconds. The uvicorn worker becomes connection-starved.

### 1.3 Single-Instance Resource Sizing

Current defaults are tuned for a 512 MB instance:

| Resource | Current Value |
|----------|---------------|
| Uvicorn workers | 1 |
| DB pool size | 2 per worker |
| DB max overflow | 3 |
| Redis max connections | 10 |

These settings cannot support 10K DAU traffic.

### 1.4 No Rate Limiting on AI Endpoints

Gemini has per-project RPM limits. Without application-level rate limiting, a
traffic spike can exhaust the quota and cause cascading failures for all users.

---

## 2. Target Architecture

### 2.1 High-Level Diagram

```
                         ┌──────────────────┐
                         │    Cloudflare     │
                         │    CDN / WAF      │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  Northflank LB    │
                         │  (auto-routed)    │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
      ┌───────▼───────┐  ┌───────▼───────┐  ┌───────▼───────┐
      │  api-public   │  │  api-public   │  │  api-public   │
      │  replica 1    │  │  replica 2    │  │  replica N    │
      │               │  │               │  │               │
      │  FastAPI +    │  │  FastAPI +    │  │  FastAPI +    │
      │  PyMediator   │  │  PyMediator   │  │  PyMediator   │
      │  (local CQRS) │  │  (local CQRS) │  │  (local CQRS) │
      └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
             ┌──────▼──────┐  ┌──▼───┐  ┌──────▼──────┐
             │   Redis     │  │MySQL │  │ Cloudinary  │
             │  (queue +   │  │(RDS /│  │ (images)    │
             │   cache)    │  │ NF)  │  │             │
             └──────┬──────┘  └──────┘  └─────────────┘
                    │
              ┌─────┼─────┐
              │           │
      ┌───────▼───┐ ┌─────▼──────┐
      │ worker-ai │ │ worker-ai  │
      │ replica 1 │ │ replica N  │
      │           │ │            │
      │ Consumes  │ │ Consumes   │
      │ AI jobs   │ │ AI jobs    │
      │ from      │ │ from       │
      │ Redis     │ │ Redis      │
      └───────────┘ └────────────┘
```

### 2.2 Messaging Strategy

Use two complementary patterns:

| Pattern | Scope | Implementation |
|---------|-------|----------------|
| **PyMediator (local)** | Within a single process | Keep as-is for commands/queries |
| **Redis job queue (distributed)** | Between services | New layer for AI and heavy async work |

The local mediator stays untouched. The new queue layer wraps around it for
cross-service jobs only.

### 2.3 What Changes for Each Endpoint Type

| Endpoint Type | Current | After |
|---------------|---------|-------|
| GET (meals, profiles, macros) | `event_bus.send(query)` | No change (local mediator) |
| PUT/DELETE (edit, delete meal) | `event_bus.send(command)` | No change (local mediator) |
| POST `/meals/image/analyze` | `event_bus.send(command)` blocks 5-10s | Enqueue job, return `202` + `job_id` |
| POST `/meal-suggestions` | `event_bus.send(command)` blocks 3-8s | Enqueue job, return `202` + `job_id` |
| POST `/meals/manual` | `event_bus.send(command)` fast | No change (no AI) |

Only AI-heavy write endpoints move to the async pattern.

---

## 3. Service Topology on Northflank

### 3.1 Service Definitions

#### `api-public` (Deployment)

- **Image:** Same Docker image as today
- **Command:** `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- **Port:** 8000 (public)
- **Min replicas:** 2
- **Max replicas:** 10
- **Autoscale on:** RPS (threshold: 200/replica) + CPU (70%)
- **Resources:** 0.5 vCPU / 512 MB per replica
- **Env vars:** All current vars + `SERVICE_ROLE=api`

#### `worker-ai` (Deployment, no public port)

- **Image:** Same Docker image
- **Command:** `python -m src.worker.main`
- **Port:** None (internal only, no HTTP traffic)
- **Min replicas:** 1
- **Max replicas:** 10
- **Autoscale on:** CPU (70%) initially; custom metric (queue depth) later
- **Resources:** 0.5 vCPU / 512 MB per replica
- **Env vars:** All current vars + `SERVICE_ROLE=worker`

#### `redis` (Add-on or Deployment)

- **Option A:** Northflank managed Redis add-on (simplest)
- **Option B:** Self-managed Redis deployment with persistence
- **Min memory:** 256 MB (queue + cache combined)
- **Max connections:** 100+

#### `mysql` (Add-on or External)

- **Keep current managed MySQL.** No changes needed initially.
- **Future:** Add read replica when query volume exceeds 500 QPS.

### 3.2 Shared Docker Image

Both `api-public` and `worker-ai` use the same image. The entrypoint
determines behavior:

```dockerfile
# Dockerfile (simplified)
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

# No CMD — set via Northflank service config
```

- API service overrides CMD to run uvicorn.
- Worker service overrides CMD to run the worker loop.

### 3.3 Networking

- `api-public` → `redis`: Private network (Northflank internal DNS)
- `api-public` → `mysql`: Private network
- `worker-ai` → `redis`: Private network
- `worker-ai` → `mysql`: Private network
- `worker-ai` → Gemini API: Public internet (outbound)

No direct communication between `api-public` and `worker-ai`. All coordination
happens through Redis (queue) and MySQL (shared state).

---

## 4. Distributed Job Queue Design

### 4.1 Queue Technology: Redis Streams

Use Redis Streams (not simple `LPUSH/BRPOP`) for reliable job processing:

- **Consumer groups** ensure each job is delivered to exactly one worker.
- **Acknowledgment** prevents job loss on worker crash.
- **Pending entries list (PEL)** enables retry of unacknowledged jobs.
- **Built into Redis** — no new infrastructure needed.

### 4.2 Job Lifecycle

```
┌────────┐    enqueue     ┌───────────┐    XREADGROUP    ┌──────────┐
│  API   │ ──────────────►│  Redis    │ ────────────────►│  Worker  │
│        │                │  Stream   │                  │          │
│        │                │           │◄─────────────────│          │
│        │    poll status │           │    XACK + update │          │
│        │◄───────────────│           │    MySQL status  │          │
└────────┘   GET /jobs/id └───────────┘                  └──────────┘
```

### 4.3 Job Schema

```python
@dataclass
class JobPayload:
    job_id: str              # UUID, returned to client
    job_type: str            # "meal_image_analysis" | "meal_suggestions" | ...
    user_id: str
    created_at: str          # ISO 8601
    priority: int            # 0 = normal, 1 = premium user
    max_retries: int         # Default 3
    retry_count: int         # Current attempt number
    payload: dict            # Job-specific data (see below)
```

#### Job Types and Payloads

**`meal_image_analysis`**
```python
{
    "meal_id": "uuid",           # Pre-created meal record (status=QUEUED)
    "image_url": "https://...",  # Cloudinary URL (already uploaded by API)
    "content_type": "image/jpeg",
    "language": "en",
    "user_description": "grilled chicken with rice",  # Optional
    "target_date": "2026-03-13",
    "timezone": "Asia/Ho_Chi_Minh"
}
```

**`meal_suggestions`**
```python
{
    "session_id": "uuid",
    "profile_snapshot": { ... },  # User profile at time of request
    "suggestion_count": 5,
    "language": "vi"
}
```

### 4.4 Job Status Model

Store in MySQL (new `jobs` table) or use Redis hash:

```
QUEUED → PROCESSING → COMPLETED
                    → FAILED → RETRYING → PROCESSING
                             → DEAD (max retries exceeded)
```

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | VARCHAR(36) PK | UUID |
| `job_type` | VARCHAR(50) | Discriminator |
| `status` | ENUM | QUEUED, PROCESSING, COMPLETED, FAILED, DEAD |
| `user_id` | VARCHAR(36) FK | Owner |
| `created_at` | DATETIME | Enqueue time |
| `started_at` | DATETIME | Worker pickup time |
| `completed_at` | DATETIME | Completion time |
| `result_ref` | VARCHAR(36) | FK to result entity (e.g., meal_id) |
| `error_message` | TEXT | Last error |
| `retry_count` | INT | Current attempt |
| `worker_id` | VARCHAR(100) | Which worker instance processed it |

### 4.5 API Contract Changes

#### Enqueue (existing endpoint, changed response)

```
POST /v1/meals/image/analyze
Content-Type: multipart/form-data

Response: 202 Accepted
{
    "job_id": "abc-123",
    "status": "queued",
    "poll_url": "/v1/jobs/abc-123",
    "estimated_wait_seconds": 5
}
```

#### Poll Status

```
GET /v1/jobs/{job_id}

Response: 200 OK
{
    "job_id": "abc-123",
    "status": "completed",        // queued | processing | completed | failed
    "created_at": "2026-03-13T10:00:00Z",
    "completed_at": "2026-03-13T10:00:06Z",
    "result": {
        "meal_id": "meal-456",    // Use existing GET /v1/meals/{id} for full data
    }
}
```

### 4.6 Dead Letter Queue (DLQ)

Jobs that fail after `max_retries` (default 3) are moved to a dead letter
stream (`jobs:dead`). Operations team can:

- Inspect failed jobs via monitoring endpoint
- Manually retry after fixing the root cause
- Alert on DLQ depth > threshold

### 4.7 Retry Policy

| Attempt | Delay | Strategy |
|---------|-------|----------|
| 1 | Immediate | First try |
| 2 | 5 seconds | Exponential backoff |
| 3 | 15 seconds | Exponential backoff |
| 4+ | Move to DLQ | Alert ops |

For rate-limit errors (HTTP 429 from Gemini), use the `Retry-After` header
value instead of fixed backoff.

---

## 5. Migration Path

### Phase 1: Add Job Queue Infrastructure (Week 1)

**Goal:** Introduce queue primitives without changing existing behavior.

1. Add `src/infra/queue/` package:
   - `job_queue_port.py` — abstract interface
   - `redis_job_queue.py` — Redis Streams implementation
   - `job_payload.py` — dataclass definitions
2. Add `src/worker/` package:
   - `main.py` — worker entrypoint (boot DI, start consumer loop)
   - `consumer.py` — Redis Stream consumer with consumer group
   - `job_router.py` — routes job types to existing handlers
3. Add `jobs` table migration.
4. Add `GET /v1/jobs/{job_id}` status endpoint.
5. Deploy `worker-ai` service on Northflank (but no traffic yet).

**Risk:** Zero. No existing behavior changes.

### Phase 2: Async Meal Image Analysis (Week 2)

**Goal:** Move `UploadMealImageImmediatelyCommand` to async pattern.

1. Modify `POST /v1/meals/image/analyze` route:
   - Upload image to Cloudinary (keep in API, fast operation).
   - Create meal record with status `QUEUED` (new status value).
   - Enqueue `meal_image_analysis` job.
   - Return `202` with `job_id`.
2. Worker picks up job and calls existing
   `UploadMealImageImmediatelyHandler` logic (minus the upload step).
3. Update Flutter client to handle `202` response:
   - Show "analyzing..." UI immediately.
   - Poll `GET /v1/jobs/{job_id}` every 2 seconds.
   - On `completed`, fetch meal via `GET /v1/meals/{id}`.

**Backward compatibility option:** Add query param `?sync=true` to keep the
old synchronous behavior during transition. Remove after client adoption.

### Phase 3: Async Meal Suggestions (Week 3)

**Goal:** Move `GenerateMealSuggestionsCommand` to async pattern.

Same pattern as Phase 2. Suggestion generation (3-8s Gemini calls) moves to
the worker.

### Phase 4: Autoscaling & Tuning (Week 4)

1. Enable Northflank autoscaling for `api-public` and `worker-ai`.
2. Tune pool sizes for multi-replica deployment:
   - `api-public`: `POOL_SIZE_PER_WORKER=5`, `POOL_MAX_OVERFLOW=10`
   - `worker-ai`: `POOL_SIZE_PER_WORKER=3`, `POOL_MAX_OVERFLOW=5`
3. Add Prometheus metrics endpoint for custom autoscaling (queue depth).
4. Load test with realistic traffic patterns.

### Phase 5: Advanced (Month 2+)

- Replace polling with push notifications (FCM) for job completion.
- Add priority queues (premium users processed first).
- Semantic caching with Pinecone for AI response deduplication.
- Pre-computed meal suggestion pool via scheduled Northflank cron jobs.

---

## 6. Caching Improvements

### 6.1 Expanded Cache Strategy

| Data | Current TTL | Proposed TTL | Reason |
|------|-------------|--------------|--------|
| User profile | 1h | 5 min (invalidate on write) | Read on every authed request |
| TDEE calculation | Not cached | 24h (invalidate on profile update) | Pure function of profile data |
| Daily macros | 1h | 5 min (invalidate on meal write) | Frequently viewed |
| Weekly budget | Not cached | 1h (invalidate on meal write) | Moderately viewed |
| Meal suggestions session | 4h | 4h (keep) | Good as-is |
| Food search results | Not cached | 30 min | Shared across users, same queries repeat |
| Meal by ID | Not cached | 10 min (invalidate on edit) | Frequent reads after creation |

### 6.2 Shared Food Cache

Food search results are user-independent. Cache at the query level:

```
Key:   food:search:{sha256(query + locale)}
Value: serialized search results
TTL:   30 minutes
```

At 10K DAU, many users search for the same foods. This can reduce FatSecret /
OpenFoodFacts API calls by 60-80%.

---

## 7. Image Pipeline Optimization

### 7.1 Current Flow (Bottleneck)

```
Client → [upload bytes to API] → API → [upload to Cloudinary] → [send bytes to Gemini]
```

The API server handles the full image bytes twice.

### 7.2 Optimized Flow

```
Client → [get pre-signed URL from API]
Client → [upload directly to Cloudinary]
Client → [send Cloudinary URL to API]
API    → [create meal record + enqueue job]
Worker → [fetch image from Cloudinary URL] → [send to Gemini]
```

**Benefits:**
- API never touches image bytes (saves bandwidth + memory).
- Upload failures don't affect the API process.
- Cloudinary handles upload retry/resumable uploads.

### 7.3 Client-Side Compression

Before upload, the Flutter client should:

- Resize to max 1280px on longest edge.
- Compress JPEG quality to 80%.
- Expected size reduction: 70-80% (8 MB → 1.5-2 MB).

Gemini does not benefit from images larger than 1280px for food recognition.

---

## 8. AI Cost & Throughput Optimization

### 8.1 Model Tiering

| Task | Current Model | Recommended | Cost Impact |
|------|---------------|-------------|-------------|
| Image analysis | gemini-2.5-flash | gemini-2.5-flash (keep) | Baseline |
| Meal name generation | gemini-2.5-flash-lite | Keep | ~60% cheaper |
| Suggestion generation | gemini-2.5-flash | gemini-2.5-flash-lite first, escalate if low quality | ~40% savings |
| Translation | gemini-2.5-flash | gemini-2.5-flash-lite | ~60% cheaper |
| Recipe generation | gemini-2.5-flash + gemini-3-flash | Keep dual-model | Load distribution |

### 8.2 Rate Limit Management

With multiple API keys across Google Cloud projects:

```
┌──────────────┐     Round-robin / least-loaded
│  Worker      │────►  Key A (Project 1): 60 RPM
│  AI Request  │────►  Key B (Project 2): 60 RPM
│              │────►  Key C (Project 3): 60 RPM
└──────────────┘       Total: 180 RPM effective
```

Implement in a `GeminiKeyRotator` service that:
- Tracks per-key usage in Redis (sliding window counter).
- Selects the least-loaded key for each request.
- Backs off a key when 429 is received.

### 8.3 Semantic Caching (Pinecone)

For meal image analysis:

1. Generate a perceptual hash or embedding of the uploaded image.
2. Query Pinecone: "has a very similar image been analyzed before?"
3. If similarity > 0.95, return cached nutrition data (skip Gemini).
4. If not, call Gemini, store result + embedding.

At scale, common foods (rice, chicken breast, salad) are photographed
thousands of times. Expected cache hit rate: 20-40%.

### 8.4 Pre-Computed Suggestion Pool

Run a Northflank cron job nightly to pre-generate meal suggestions for
common profile archetypes:

| Archetype | Calories | Diet | Example |
|-----------|----------|------|---------|
| Weight loss, no restrictions | 1500 | Any | "Grilled chicken salad" |
| Muscle gain, high protein | 2800 | Any | "Steak with sweet potato" |
| Vegetarian maintenance | 2000 | Vegetarian | "Tofu stir fry" |
| ... | ... | ... | ... |

When a user requests suggestions, first try to match from the pre-computed
pool. Only invoke Gemini for highly personalized or niche requests.

---

## 9. Observability & Reliability

### 9.1 Structured Logging

Add correlation IDs that flow across services:

```
API log:  {"request_id": "abc", "job_id": "xyz", "user_id": "u1", "action": "enqueue"}
Worker log: {"job_id": "xyz", "user_id": "u1", "action": "gemini_call", "latency_ms": 4200}
```

### 9.2 Metrics (Prometheus)

| Metric | Type | Labels |
|--------|------|--------|
| `jobs_enqueued_total` | Counter | `job_type` |
| `jobs_completed_total` | Counter | `job_type`, `status` |
| `jobs_processing_duration_seconds` | Histogram | `job_type` |
| `queue_depth` | Gauge | `stream_name` |
| `queue_oldest_pending_age_seconds` | Gauge | `stream_name` |
| `gemini_requests_total` | Counter | `model`, `status` |
| `gemini_latency_seconds` | Histogram | `model` |
| `gemini_rate_limit_hits_total` | Counter | `api_key` |

### 9.3 Circuit Breaker on Gemini

If Gemini error rate exceeds 30% in a 60-second window:

1. Open circuit — stop sending requests.
2. Return cached/fallback results for analysis jobs.
3. Mark affected jobs as `FAILED` with `retryable=true`.
4. After 30 seconds, try a single probe request.
5. If probe succeeds, close circuit and resume processing.

### 9.4 Health Checks

Extend existing health endpoints:

```
GET /health/queue    → Redis Stream connectivity + queue depth
GET /health/worker   → Worker heartbeat (workers publish heartbeat to Redis every 30s)
GET /health/gemini   → Last successful Gemini call timestamp + error rate
```

### 9.5 Alerting Rules

| Condition | Severity | Action |
|-----------|----------|--------|
| Queue depth > 500 for 5 min | Warning | Scale up workers |
| Queue depth > 2000 for 2 min | Critical | Page on-call |
| DLQ depth > 10 | Warning | Investigate failures |
| Gemini error rate > 20% for 3 min | Critical | Check quota/outage |
| Job wait time p95 > 30s | Warning | Scale up workers |
| Worker heartbeat missing > 60s | Critical | Worker is dead |

---

## 10. Cost Projections

### 10.1 Assumptions

| Metric | Value |
|--------|-------|
| DAU | 10,000 |
| AI calls per user per day | 3-5 |
| Average Gemini latency | 5 seconds |
| Gemini cost per 1M input tokens | $0.10 (Flash Lite) — $0.15 (Flash) |
| Average tokens per meal analysis | ~2,000 input + ~500 output |
| Cache hit rate (after optimization) | 30% |

### 10.2 Monthly Estimate

| Line Item | Before (single instance) | After (multi-service) | Delta |
|-----------|-------------------------|-----------------------|-------|
| API compute | 1 x 1 vCPU / 1 GB = ~$25 | 3 x 0.5 vCPU / 512 MB = ~$40 | +$15 |
| Worker compute | $0 (same process) | 2 x 0.5 vCPU / 512 MB = ~$25 | +$25 |
| Redis | Basic tier ~$15 | Standard tier ~$30 | +$15 |
| MySQL | No change | No change | $0 |
| **Infra subtotal** | **~$40** | **~$95** | **+$55** |
| Gemini API (no caching) | ~$150 | ~$150 | $0 |
| Gemini API (with 30% cache hit) | — | ~$105 | **-$45** |
| Gemini API (with model tiering) | — | ~$80 | **-$70** |
| **AI subtotal** | **~$150** | **~$80** | **-$70** |
| **Total** | **~$190** | **~$175** | **-$15** |

**Net result:** Roughly cost-neutral, but with 10x the capacity headroom and
significantly better user experience (fast API responses, no timeouts).

### 10.3 Scaling Cost Curve

| DAU | API replicas | Worker replicas | Est. monthly cost |
|-----|-------------|-----------------|-------------------|
| 1,000 | 2 | 1 | ~$80 |
| 5,000 | 3 | 2 | ~$130 |
| 10,000 | 4 | 3 | ~$175 |
| 25,000 | 6 | 5 | ~$280 |
| 50,000 | 10 | 8 | ~$450 |

These are compute + cache estimates only. AI API costs scale linearly with DAU
unless cache hit rates improve.

---

## 11. Queue Provider Switching (Upstash / Dedicated)

The job queue supports two Redis backends selected at startup via environment
variables. No code changes are required to switch providers.

### 11.1 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `QUEUE_ENABLED` | No | Set to `true` to enable the queue (default: `false`) |
| `QUEUE_PROVIDER` | No | `upstash` or `dedicated` (default: `upstash`) |
| `UPSTASH_REDIS_URL` | When `upstash` | Full Redis URL from Upstash dashboard |
| `DEDICATED_REDIS_URL` | No | Override for dedicated; else uses `REDIS_*` / `redis_url` |

### 11.2 Upstash (Default)

Use for development, staging, or low-traffic production (~1K DAU).

```env
QUEUE_ENABLED=true
QUEUE_PROVIDER=upstash
UPSTASH_REDIS_URL=rediss://default:YOUR_TOKEN@us1-xxx.upstash.io:6379
```

Get the URL from [Upstash Console](https://console.upstash.com/) → your Redis database → REST API / Connect.

### 11.3 Dedicated Redis

Use for higher throughput or when you run Redis on Northflank / managed provider.

**Option A: Reuse main Redis (cache + queue on same instance)**

```env
QUEUE_ENABLED=true
QUEUE_PROVIDER=dedicated
# DEDICATED_REDIS_URL not set — uses REDIS_HOST, REDIS_PORT, etc.
```

**Option B: Separate Redis for queue**

```env
QUEUE_ENABLED=true
QUEUE_PROVIDER=dedicated
DEDICATED_REDIS_URL=redis://queue-host:6379/0
```

### 11.4 Switching Procedure

1. Update environment variables for the new provider.
2. Restart the application (startup-time selection; no hot-switch).
3. If switching from Upstash to dedicated: ensure the new Redis is reachable and that queue data is migrated or acceptable to lose (jobs in flight will be dropped on switch).

### 11.5 Validation

- Invalid `QUEUE_PROVIDER` → `ValueError` at startup.
- `QUEUE_PROVIDER=upstash` without `UPSTASH_REDIS_URL` → `ValueError` at startup.
- No automatic fallback; explicit provider selection only.

---

## Appendix A: New File Structure

```
src/
├── api/                          # Unchanged
├── app/                          # Unchanged
├── domain/
│   └── ports/
│       └── job_queue_port.py     # NEW: Abstract queue interface
├── infra/
│   ├── queue/                    # NEW
│   │   ├── __init__.py
│   │   ├── job_payload.py        # Job dataclasses
│   │   ├── redis_job_queue.py    # Redis Streams implementation
│   │   └── job_status.py         # Status enum + DB model
│   └── resilience/               # NEW
│       ├── __init__.py
│       ├── circuit_breaker.py    # Gemini circuit breaker
│       └── rate_limiter.py       # Per-key rate tracking
└── worker/                       # NEW
    ├── __init__.py
    ├── main.py                   # Entrypoint: boot DI, start consumer
    ├── consumer.py               # Redis Stream consumer loop
    ├── job_router.py             # Route job_type → handler
    └── health.py                 # Worker heartbeat publisher
```

## Appendix B: Key Interfaces

### JobQueuePort

```python
from abc import ABC, abstractmethod
from typing import Optional
from src.infra.queue.job_payload import JobPayload, JobStatus

class JobQueuePort(ABC):
    @abstractmethod
    async def enqueue(self, payload: JobPayload) -> str:
        """Enqueue a job. Returns job_id."""

    @abstractmethod
    async def dequeue(self, job_types: list[str], block_ms: int = 5000) -> Optional[JobPayload]:
        """Consume next available job (blocks up to block_ms)."""

    @abstractmethod
    async def ack(self, job_id: str) -> None:
        """Acknowledge successful processing."""

    @abstractmethod
    async def nack(self, job_id: str, error: str) -> None:
        """Report processing failure (triggers retry or DLQ)."""

    @abstractmethod
    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        """Get current job status."""
```

### Worker Consumer Loop

```python
async def consume_loop(queue: JobQueuePort, router: JobRouter):
    while True:
        job = await queue.dequeue(["meal_image_analysis", "meal_suggestions"])
        if job is None:
            continue
        try:
            await router.handle(job)
            await queue.ack(job.job_id)
        except RetryableError as e:
            await queue.nack(job.job_id, str(e))
        except Exception as e:
            logger.error(f"Fatal error processing job {job.job_id}: {e}")
            await queue.nack(job.job_id, str(e))
```

## Appendix C: Flutter Client Changes

### Async Meal Analysis Flow

```dart
// 1. Upload image and get job_id
final response = await apiService.post('/v1/meals/image/analyze', formData);
final jobId = response['job_id'];  // 202 response

// 2. Show analyzing UI
state = MealAnalyzingState(jobId: jobId);

// 3. Poll for completion
final meal = await _pollForResult(jobId);

Future<Meal> _pollForResult(String jobId) async {
  const maxAttempts = 30;
  const interval = Duration(seconds: 2);

  for (var i = 0; i < maxAttempts; i++) {
    final status = await apiService.get('/v1/jobs/$jobId');

    if (status['status'] == 'completed') {
      final mealId = status['result']['meal_id'];
      return await apiService.get('/v1/meals/$mealId');
    }

    if (status['status'] == 'failed') {
      throw MealAnalysisException(status['error']);
    }

    await Future.delayed(interval);
  }

  throw TimeoutException('Analysis took too long');
}
```

### Backward Compatibility

During migration, the client can detect the response code:

```dart
if (response.statusCode == 200) {
  // Old sync path — parse meal directly
} else if (response.statusCode == 202) {
  // New async path — poll for result
}
```
