---
phase: 2
title: "Graph Scaffold And Feature Flags"
status: completed
priority: P1
effort: "1d"
dependencies: [1]
---

# Phase 2: Graph Scaffold And Feature Flags

## Context Links

- Plan: `plans/260707-1348-meal-analyze-langgraph-provider/plan.md`
- Settings: `src/infra/config/settings.py`
- Existing fast-path policy: `src/domain/services/meal_analysis/fast_path_policy.py`
- Dependency wiring: `src/api/dependencies/event_bus.py`
- LangGraph docs: `https://docs.langchain.com/oss/python/langgraph/graph-api`

## Overview

Add LangGraph and create the default-off app-layer graph scaffold. The scaffold
must compile and be testable without changing handler routing yet.

## Key Insights

- Graph belongs in application layer, not domain.
- Nodes should be coarse workflow steps.
- Feature flags must allow instant rollback to legacy handlers.
- Current `claudekit` CLI was unavailable during planning, so files were created manually in standard plan shape.

## Requirements

- Functional: `AI_MEAL_ANALYZE_GRAPH_ENABLED=false` keeps legacy behavior.
- Functional: graph can compile with a minimal state and no provider calls.
- Non-functional: no vendor SDK imports in graph nodes.
- Non-functional: dependency updates are pinned/locked consistently.

## Architecture

```text
src/app/graphs/meal_analyze/
  state.py       # TypedDict or Pydantic state for graph IO
  graph.py       # build/compile graph
  nodes.py       # coarse node functions, service-backed
  quality_gate.py
```

Initial graph nodes should be minimal:

```text
prepare_input -> select_mode -> complete
```

Later phases fill real behavior.

## Related Code Files

- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `uv.lock`
- Modify: `src/infra/config/settings.py`
- Create: `src/app/graphs/meal_analyze/__init__.py`
- Create: `src/app/graphs/meal_analyze/state.py`
- Create: `src/app/graphs/meal_analyze/graph.py`
- Create: `src/app/graphs/meal_analyze/nodes.py`
- Create: `src/app/graphs/meal_analyze/quality_gate.py`
- Create: `tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py`
- Modify: `tests/unit/architecture/test_meal_analyze_graph_boundaries.py`

## Tests Before

1. Add test that graph settings default to disabled.
2. Add failing test that `build_meal_analyze_graph()` compiles.
3. Add failing test that graph invocation returns input-compatible state without side effects.
4. Add/update architecture test:
   - `src/domain` cannot import LangGraph.
   - `src/app/graphs/meal_analyze` cannot import `openai`, `langchain_openai`, `langchain_cloudflare`, `httpx` provider clients, `sentry_sdk`, or SQLAlchemy.

## Refactor

1. Add `langgraph` dependency.
2. Add settings:

```text
AI_MEAL_ANALYZE_GRAPH_ENABLED=false
AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED=false
AI_MEAL_ANALYZE_EXTERNAL_PROVIDER_TIMEOUT_SECONDS=5
AI_MEAL_ANALYZE_GRAPH_VERSION=v1
```

3. Add graph state and compile function.
4. Keep all graph code app-layer only.

## Tests After

1. Verify graph compiles.
2. Verify disabled flag remains false by default.
3. Verify architecture guardrails pass.

## Implementation Steps

1. Add LangGraph dependency with the repo package manager.
2. Add settings fields with conservative defaults.
3. Create graph package and minimal state.
4. Create `build_meal_analyze_graph()` and `run_meal_analyze_graph()` helpers.
5. Add no-op nodes that preserve state.
6. Add unit tests and architecture tests.
7. Run focused tests and import checks.

## Todo List

- [x] LangGraph dependency added and lockfile updated.
- [x] Feature flags added with safe defaults.
- [x] Graph package created under `src/app/graphs/meal_analyze/`.
- [x] Graph compile test passes.
- [x] Architecture guardrails pass.

## Success Criteria

- [x] App imports with new dependency.
- [x] Graph is default-off.
- [x] No handler behavior changes.
- [x] Tests pass:

```bash
uv run pytest tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py tests/unit/domain/services/meal_analysis/test_fast_path_policy.py tests/unit/architecture/test_meal_analyze_graph_boundaries.py -q
```

## Risk Assessment

- Risk: LangGraph dependency conflicts with existing LangChain versions.
  Mitigation: add dependency in isolation and run import tests before integration.
- Risk: graph package leaks infrastructure imports.
  Mitigation: architecture test blocks it before graph grows.

## Security Considerations

- Feature flags must not expose provider credentials.
- Graph state must not store raw image bytes in logs or metrics.

## Regression Gate

```bash
uv run python -m compileall src/app/graphs/meal_analyze src/infra/config/settings.py
uv run pytest tests/unit/app/graphs/test_meal_analyze_graph_scaffold.py tests/unit/architecture/test_meal_analyze_graph_boundaries.py -q
```

## Next Steps

Proceed to Phase 3 when graph scaffold is default-off and import-safe.
