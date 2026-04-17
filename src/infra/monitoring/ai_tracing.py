"""Sentry gen_ai span helpers for AI call sites."""
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

import sentry_sdk


@asynccontextmanager
async def trace_ai_call(
    *,
    model: str,
    operation: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> AsyncGenerator[None, None]:
    """Async context manager that wraps a single LLM invocation in a gen_ai.request span."""
    with sentry_sdk.start_span(op="gen_ai.request", name=operation) as span:
        span.set_data("gen_ai.request.model", model)
        if input_tokens is not None:
            span.set_data("gen_ai.usage.input_tokens", input_tokens)
        if output_tokens is not None:
            span.set_data("gen_ai.usage.output_tokens", output_tokens)
        yield


@contextmanager
def trace_ai_phase(
    *,
    phase: str,
    description: str,
) -> Generator[None, None, None]:
    """Sync context manager that wraps a pipeline phase in a gen_ai.invoke_agent span."""
    with sentry_sdk.start_span(op="gen_ai.invoke_agent", name=description) as span:
        span.set_data("gen_ai.agent.name", phase)
        yield
