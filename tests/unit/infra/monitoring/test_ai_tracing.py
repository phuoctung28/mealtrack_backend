"""Unit tests for AI tracing helpers."""
from unittest.mock import MagicMock, patch

import pytest

from src.infra.monitoring.ai_tracing import trace_ai_call, trace_ai_phase


class TestTraceAiCall:
    """trace_ai_call is an async context manager that starts a Sentry gen_ai.request span."""

    @pytest.mark.asyncio
    async def test_sets_span_op_and_name(self):
        mock_span = MagicMock()
        with patch("sentry_sdk.start_span", return_value=mock_span) as mock_start:
            async with trace_ai_call(model="gemini-2.5-flash", operation="vision_analysis"):
                pass
        mock_start.assert_called_once_with(
            op="gen_ai.request",
            name="vision_analysis",
        )

    @pytest.mark.asyncio
    async def test_sets_model_attribute(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        with patch("sentry_sdk.start_span", return_value=mock_span):
            async with trace_ai_call(model="gemini-2.5-flash", operation="test_op"):
                pass
        mock_span.set_attribute.assert_any_call("gen_ai.request.model", "gemini-2.5-flash")

    @pytest.mark.asyncio
    async def test_sets_token_attributes_when_provided(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        with patch("sentry_sdk.start_span", return_value=mock_span):
            async with trace_ai_call(
                model="gemini-2.5-flash",
                operation="test_op",
                input_tokens=100,
                output_tokens=50,
            ):
                pass
        mock_span.set_attribute.assert_any_call("gen_ai.usage.input_tokens", 100)
        mock_span.set_attribute.assert_any_call("gen_ai.usage.output_tokens", 50)


class TestTraceAiPhase:
    """trace_ai_phase is a sync context manager for pipeline phases."""

    def test_sets_span_op_and_name(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        with patch("sentry_sdk.start_span", return_value=mock_span) as mock_start:
            with trace_ai_phase(phase="vision_analysis", description="PHASE-1"):
                pass
        mock_start.assert_called_once_with(
            op="gen_ai.invoke_agent",
            name="PHASE-1",
        )

    def test_sets_phase_attribute(self):
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        with patch("sentry_sdk.start_span", return_value=mock_span):
            with trace_ai_phase(phase="meal_names", description="Phase 1: Generate meal names"):
                pass
        mock_span.set_attribute.assert_any_call("gen_ai.agent.name", "meal_names")
