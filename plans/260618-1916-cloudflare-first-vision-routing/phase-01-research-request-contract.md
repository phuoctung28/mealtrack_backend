---
phase: 1
title: "Research request contract"
status: pending
priority: P1
effort: "2h"
dependencies: []
---

# Phase 1: Research request contract

## Overview

Confirm the exact Cloudflare Workers AI vision request/response contract before implementation. The goal is to avoid building against a table that says `Vision Yes` but a request shape that rejects image payloads.

## Requirements

- Functional: prove a payload shape for `@cf/google/gemma-4-26b-a4b-it` that accepts image input and returns text suitable for JSON extraction.
- Functional: identify fallback candidate only if Gemma 4 cannot accept image input in practice.
- Non-functional: do not require production secrets in tests or docs.
- Non-functional: do not log raw image bytes, base64 strings, raw prompts, or provider response bodies.

## Architecture

Use Workers AI REST for vision:

```json
{
  "messages": [
    {"role": "system", "content": "vision system prompt"},
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "meal analysis prompt"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }
  ],
  "max_tokens": 8192,
  "temperature": 0.2
}
```

If this contract fails live, test the model's documented OpenAI-compatible endpoint before falling back to raw `image` fields. Avoid deprecated `@cf/unum/uform-gen2-qwen-500m`.

## Related Code Files

- Read: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/ai/providers/cloudflare_workers_ai_provider.py`
- Read: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/services/ai/ai_model_manager.py`
- Read: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/infra/adapters/vision_ai_service.py`
- Read: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/src/domain/services/prompts/system_prompts.py`
- Read: `/Users/alexnguyen/Desktop/Nut/mealtrack_backend/docs/external-services.md`

## Implementation Steps

1. Fetch current Cloudflare raw schema for `@cf/google/gemma-4-26b-a4b-it` and confirm `messages[].content[].image_url`.
2. If credentials are locally available, run one manual dry-run with a tiny known image and a strict JSON prompt. Do not commit the image or secrets.
3. Record accepted response shapes to normalize: `result.response`, `result.choices[0].message.content`, plain `response`, and direct text.
4. Decide whether to send `response_format`. Default: skip it unless the live dry-run proves it works with image payloads.
5. Document the final contract in `docs/external-services.md` during Phase 4.

## Todo List

- [ ] Confirm Gemma 4 vision input schema.
- [ ] Confirm response shape normalization.
- [ ] Decide whether JSON mode is safe for vision.
- [ ] Confirm no extra Cloudflare license acceptance is needed for the selected primary model.

## Success Criteria

- [ ] Accepted CF vision request payload is known.
- [ ] Primary model and fallback policy are explicit.
- [ ] Implementation can proceed without guessing request/response fields.

## Risk Assessment

Risk: Cloudflare docs expose `Vision Yes` but REST schema is inconsistent. Mitigation: verify raw schema and, if credentials exist, one live dry-run before coding.

Risk: JSON mode rejects image messages. Mitigation: rely on existing JSON extraction first; add JSON mode only after evidence.

## Security Considerations

Never paste real API tokens into plan files, test fixtures, or logs. Manual dry-run commands must use env vars.

## Next Steps

Proceed to Phase 2 once the payload and response shape are known.
