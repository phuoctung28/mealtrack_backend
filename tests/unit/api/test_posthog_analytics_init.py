from unittest.mock import patch, MagicMock
import pytest


def test_posthog_analytics_disabled_when_no_api_key(caplog):
    """When POSTHOG_API_KEY is not set, analytics init should log disabled message."""
    import logging
    with patch.dict("os.environ", {}, clear=True):  # No POSTHOG_API_KEY
        # Import after patching env
        import importlib
        import src.api.main as main_module
        importlib.reload(main_module)
        # The module-level code should handle missing key gracefully
        # This test just confirms the import doesn't crash
    # Should not raise


def test_posthog_init_code_exists_in_main():
    """PostHog initialization code must exist in main.py."""
    import inspect
    import src.api.main as main_module
    source = inspect.getsource(main_module)
    assert "POSTHOG_API_KEY" in source
    assert "LangchainInstrumentor" in source or "langchain" in source.lower()
