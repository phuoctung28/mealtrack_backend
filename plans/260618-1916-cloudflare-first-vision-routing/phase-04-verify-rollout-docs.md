---
phase: 4
title: "Verify rollout docs"
status: pending
priority: P1
effort: "2h"
dependencies: [3]
---

# Phase 4: Verify rollout docs

## Overview

Verify the CF-first vision path and update operational docs so production rollout is explicit and reversible.

## Requirements

- Functional: all focused tests pass.
- Functional: docs explain CF vision, env vars, model choice, fallback order, and rollback.
- Non-functional: compile/lint checks run on touched Python files.
- Non-functional: rollout can be disabled without redeploying code by env var.

## Architecture

Verification pyramid:
- Provider unit tests for request/response contract.
- Model manager unit tests for routing and fallback order.
- Existing vision service tests to ensure provider-agnostic scan flow remains intact.
- Optional live smoke only when credentials are available.

## Related Code Files

- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/external-services.md`
- Modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/project-roadmap.md`
- Optional modify: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/troubleshooting.md`
- Run tests covering:
  - `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py`
  - `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/tests/unit/infra/services/ai/test_ai_model_manager.py`

## Implementation Steps

1. Run provider tests:
   `uv run pytest tests/unit/infra/services/ai/providers/test_cloudflare_workers_ai_provider.py -q`
2. Run model-manager tests:
   `uv run pytest tests/unit/infra/services/ai/test_ai_model_manager.py -q`
3. Run focused vision/AI suite:
   `uv run pytest tests/unit/infra/services/ai tests/unit/infra/adapters -q`
4. Run lint/compile on touched files:
   `uv run ruff check src/infra/services/ai src/infra/config tests/unit/infra/services/ai`
   `uv run python -m compileall src/infra/services/ai src/infra/config`
5. Update docs with:
   - CF vision fallback chain.
   - env vars and recommended Render values.
   - rollback: `CLOUDFLARE_WORKERS_AI_VISION_ENABLED=false`.
   - warning that `@cf/unum/uform-gen2-qwen-500m` is deprecated.
6. If credentials exist, run one manual smoke outside tests with a non-sensitive sample image and confirm scan JSON validates. Do not commit sample image.

## Todo List

- [ ] Provider tests pass.
- [ ] Manager tests pass.
- [ ] Focused AI suite passes.
- [ ] Ruff and compile pass.
- [ ] Docs and roadmap updated.
- [ ] Rollback env documented.

## Success Criteria

- [ ] Local verification commands pass or blocker is documented.
- [ ] Production rollout steps are clear.
- [ ] Rollback is one env-var change.
- [ ] No docs still claim vision is Gemini-only.

## Risk Assessment

Risk: CF returns lower nutrition quality than Gemini. Mitigation: ship with Gemini fallback, smoke test before rollout, and monitor provider success/failure plus user-visible scan failures.

Risk: CF outage causes scan delay before Gemini fallback. Mitigation: keep timeout bounded and circuit breaker behavior active for 429/5xx/timeout.

## Security Considerations

Production docs must not include secrets. Logs and docs must avoid raw image URLs and base64 payloads.

## Next Steps

After implementation, set Render env:

```text
CLOUDFLARE_WORKERS_AI_ENABLED=true
CLOUDFLARE_WORKERS_AI_VISION_ENABLED=true
CLOUDFLARE_WORKERS_AI_VISION_MODEL=@cf/google/gemma-4-26b-a4b-it
CLOUDFLARE_WORKERS_AI_VISION_PURPOSES=meal_scan,ingredient_scan
```

Keep `GOOGLE_API_KEY` configured for Gemini fallback.
