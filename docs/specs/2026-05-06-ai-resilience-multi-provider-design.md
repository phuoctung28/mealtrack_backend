# AI Resilience & Multi-Provider Design

**Date:** 2026-05-06  
**Status:** Approved  
**Author:** Claude Code

## Problem

All AI endpoints use `gemini-2.5-flash` variants, creating a single point of failure. When Google experiences capacity issues (503 errors), all AI features fail simultaneously. Current state:

- 7 AI-dependent endpoints sharing same model pool
- Meal suggestions make 5 AI calls per request (bottleneck)
- No fallback when model fails - SDK retries same model 5x then gives up
- 503 errors can reach 45% during Google capacity spikes
- High volume traffic (50+ concurrent users) amplifies impact

## Solution

Provider-agnostic AI layer with circuit breaker pattern and automatic fallback chain.

### Architecture

```
Handler → AIModelManager → ProviderCircuitBreaker → Provider Adapter
               ↓                     ↓                     ↓
       [selects provider]    [tracks health]      [Gemini/Kimi/...]
               ↓                     ↓                     ↓
       [fallback chain]      [opens circuit]      [executes request]
```

### New Files

| File | Purpose |
|------|---------|
| `src/domain/ports/ai_provider_port.py` | Abstract interface for any AI provider |
| `src/infra/services/ai/ai_model_manager.py` | Provider-agnostic manager with fallback chain |
| `src/infra/services/ai/provider_circuit_breaker.py` | Track health per provider/model |
| `src/infra/services/ai/providers/gemini_provider.py` | Gemini implementation of AIProviderPort |
| `src/infra/services/ai/providers/kimi_provider.py` | Kimi implementation (stub for future) |

### Modified Files

| File | Change |
|------|--------|
| `meal_generation_service.py` | Use AIModelManager instead of GeminiModelManager |
| `vision_ai_service.py` | Use AIModelManager for vision calls |
| `gemini_model_manager.py` | Refactor into GeminiProvider |

## Model Distribution Strategy

| Endpoint | Criticality | Primary | Fallback 1 | Fallback 2 |
|----------|-------------|---------|------------|------------|
| Meal Scan | High | `gemini-2.5-flash` | `gemini-2.5-flash-lite` | Kimi (future) |
| Ingredient Scan | Medium | `gemini-2.5-flash-lite` | `gemini-2.5-flash` | - |
| Parse Meal Text | Medium | `gemini-2.5-flash-lite` | `gemini-2.5-flash` | Kimi (future) |
| Barcode Lookup | Low | `gemini-2.5-flash-lite` | `gemini-2.5-flash` | Kimi (future) |
| Meal Names | Medium | `gemini-2.5-flash-lite` | `gemini-2.5-flash` | Kimi (future) |
| Recipe Gen (slot 0,2) | High | `gemini-2.5-flash` | `gemini-2.5-flash-lite` | - |
| Recipe Gen (slot 1,3) | High | `gemini-2.5-flash-lite` | `gemini-2.5-flash` | - |
| Discovery | Medium | `gemini-2.5-flash-lite` | `gemini-2.5-flash` | - |

**Distribution Logic:**
- Critical paths (vision/meal scan): flash → flash-lite → Kimi
- Medium/Low (text generation): flash-lite → flash → Kimi
- Recipe generation: Alternates slots to spread load across pools

## Circuit Breaker Design

### States

```
CLOSED (normal) → [5 failures in 60s] → OPEN (block)
                                            ↓
                                    [30s cooldown]
                                            ↓
CLOSED ← [success] ← HALF-OPEN (test 1 request)
```

### Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `failure_threshold` | 5 | Trigger after 5 consecutive failures |
| `failure_window` | 60 seconds | Rolling window for counting |
| `cooldown_period` | 30 seconds | How long circuit stays open |
| `half_open_requests` | 1 | Test requests before closing |

### Error Types That Trip Circuit

| Error | Trips Circuit? |
|-------|----------------|
| 503 UNAVAILABLE | Yes |
| 429 RESOURCE_EXHAUSTED | Yes |
| 500 INTERNAL_ERROR | Yes |
| Timeout | Yes |
| 400 BAD_REQUEST | No (client error) |
| JSON parse error | No (response issue) |

## Fallback Execution Logic

```
1. Get fallback chain for purpose: [flash, flash-lite, kimi]
2. Filter out OPEN circuits: [flash, flash-lite]
3. Try primary (flash):
   ├─ Success → return result
   └─ Failure (503) → record failure, try next
4. Try fallback (flash-lite):
   ├─ Success → return result
   └─ Failure → record failure, try next
5. All failed → raise AIUnavailableError
```

**Key Behaviors:**
- No extra retries (SDK already retries 5x)
- Skip models with OPEN circuits
- If all circuits OPEN, force try first model (HALF-OPEN)
- Log all fallback events for observability

## Error Handling

### Error Classes

```python
class AIError(Exception):
    """Base class for AI-related errors"""

class AIUnavailableError(AIError):
    """All models/providers exhausted"""

class AIPartialResultError(AIError):
    """Some results succeeded, some failed (batch operations)"""
```

### Handler Responses

| Endpoint | On Total Failure | On Partial Failure |
|----------|------------------|-------------------|
| Meal Scan | 503 + retry message | N/A |
| Ingredient Scan | 503 + retry message | N/A |
| Meal Suggestions | Return partial results | Return what succeeded |
| Recipes | Return partial results | Return what succeeded |
| Barcode | Fall back to "unknown product" | N/A |

### HTTP Response Codes

| Scenario | Status Code |
|----------|-------------|
| Success | 200 |
| Partial success | 200 (with warning field) |
| Total AI failure | 503 |
| Invalid input | 400 |

## Testing Strategy

### Unit Tests

| Component | Test Cases |
|-----------|------------|
| `ProviderCircuitBreaker` | State transitions, failure counting, cooldown, thread safety |
| `AIModelManager` | Model selection, fallback ordering, circuit filtering |
| `ResilientExecutor` | Primary success, fallback on failure, all-fail, partial batch |
| `GeminiProvider` | Request formatting, response parsing, error classification |

### Integration Tests

- Fallback on 503: Primary fails → secondary succeeds
- Circuit opens after threshold: 5 failures → circuit OPEN
- Partial batch results: Some prompts fail → return successful ones
- Circuit recovery: After cooldown → HALF-OPEN → success → CLOSED

### Load Testing

| Test | Success Criteria |
|------|------------------|
| 50 concurrent requests | < 1% failure rate |
| Circuit breaker trip | Traffic shifts within 5 requests |
| Sustained fallback | System stable on fallback for 5 min |

### Observability Metrics

- `ai_request_total`: Total requests by model
- `ai_request_failures`: Failures by model and error type
- `ai_fallback_total`: Fallback activations by purpose
- `ai_circuit_state`: Circuit state gauge (0=closed, 1=open, 2=half-open)
- `ai_request_latency`: Latency histogram by model

## Future: Kimi Integration

Kimi provider is stubbed for future implementation when upgraded to Tier 1 (200 RPM). Current Tier 0 (~3 RPM) is insufficient for fallback traffic.

When ready:
1. Implement `KimiProvider` following `AIProviderPort`
2. Add Kimi models to fallback chains
3. Configure circuit breaker for Kimi models
4. Note: Kimi vision support TBD - may not support image analysis

## Success Criteria

- < 1% failure rate under normal operation
- Automatic fallback within 1 request when primary fails
- Circuit opens within 5 failures, recovers after 30s cooldown
- No code changes needed to add new providers (just implement port)
