---
status: completed
created: 260627-1322
title: meal scan prompt and beverage simplification
source_report: ../reports/brainstorm-260627-1322-meal-scan-prompt-and-beverage-simplification-report.md
---

# Meal Scan Prompt And Beverage Simplification

## Overview

Rework meal image analysis so meal scan has one contract: analyze visible
edible or drinkable intake as a normal meal. Remove packaged-beverage routing
from `/v1/meals/image/analyze` and `/v1/meals/scan-by-url`.

## Phases

| Phase | Status | File | Goal |
|-------|--------|------|------|
| 1 | completed | [phase-01-contract-tests.md](./phase-01-contract-tests.md) | Lock approved behavior with tests |
| 2 | completed | [phase-02-prompt-contract.md](./phase-02-prompt-contract.md) | Rewrite cached vision prompt contract |
| 3 | completed | [phase-03-handler-simplification.md](./phase-03-handler-simplification.md) | Remove beverage hydration routing |
| 4 | completed | [phase-04-docs-and-verification.md](./phase-04-docs-and-verification.md) | Update docs and run gates |

## Dependencies

- Existing OpenAI structured vision path through `VisionAIService`.
- Existing `VisionNutritionResponse` and `VisionResponseParser` contracts.
- Existing hydration APIs stay available but out of meal scan scope.

## Success Criteria

- Caloric packaged beverages scanned as normal meals.
- Meal scan does not create `hydration_entries`.
- Non-food images still reject.
- Prompt remains one static cache-friendly system message.
- Upload and scan-by-url behavior match.

## Out Of Scope

- New beverage-specific scan endpoint.
- Mobile UI changes.
- Hydration catalog changes.
- Provider routing changes.
