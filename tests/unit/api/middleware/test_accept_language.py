"""Tests for Accept-Language middleware."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.middleware.accept_language import (
    AcceptLanguageMiddleware,
    get_request_language,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
)


@pytest.fixture
def app():
    """Create test app with middleware."""
    app = FastAPI()
    app.add_middleware(AcceptLanguageMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"language": get_request_language(request)}

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestAcceptLanguageMiddleware:
    """Tests for AcceptLanguageMiddleware."""

    def test_parses_simple_language_code(self, client):
        """Test parsing simple language code like 'vi'."""
        response = client.get("/test", headers={"Accept-Language": "vi"})
        assert response.json()["language"] == "vi"

    def test_parses_language_with_region(self, client):
        """Test parsing language with region like 'en-US'."""
        response = client.get("/test", headers={"Accept-Language": "en-US"})
        assert response.json()["language"] == "en"

    def test_parses_multiple_languages_takes_first(self, client):
        """Test parsing multiple languages, takes first."""
        response = client.get(
            "/test",
            headers={"Accept-Language": "vi,en;q=0.9,fr;q=0.8"}
        )
        assert response.json()["language"] == "vi"

    def test_defaults_to_en_when_no_header(self, client):
        """Test defaults to 'en' when header missing."""
        response = client.get("/test")
        assert response.json()["language"] == DEFAULT_LANGUAGE

    def test_defaults_to_en_for_unsupported_language(self, client):
        """Test defaults to 'en' for unsupported language."""
        response = client.get("/test", headers={"Accept-Language": "xx"})
        assert response.json()["language"] == DEFAULT_LANGUAGE

    def test_handles_empty_header(self, client):
        """Test handles empty Accept-Language header."""
        response = client.get("/test", headers={"Accept-Language": ""})
        assert response.json()["language"] == DEFAULT_LANGUAGE

    @pytest.mark.parametrize("lang", list(SUPPORTED_LANGUAGES))
    def test_all_supported_languages(self, client, lang):
        """Test all supported languages are recognized."""
        response = client.get("/test", headers={"Accept-Language": lang})
        assert response.json()["language"] == lang

    def test_case_insensitive(self, client):
        """Test language parsing is case insensitive."""
        response = client.get("/test", headers={"Accept-Language": "VI"})
        assert response.json()["language"] == "vi"

    def test_parses_quality_factor_correctly(self, client):
        """Test parsing language with quality factor."""
        response = client.get(
            "/test",
            headers={"Accept-Language": "en-US,en;q=0.9,vi;q=0.8"}
        )
        # Should take first language (en-US -> en after stripping region)
        assert response.json()["language"] == "en"


class TestGetRequestLanguage:
    """Tests for get_request_language helper."""

    def test_returns_default_when_no_state(self):
        """Test returns default when request has no state."""
        class MockRequest:
            state = type('state', (), {})()

        assert get_request_language(MockRequest()) == DEFAULT_LANGUAGE

    def test_returns_language_from_state(self):
        """Test returns language from request state."""
        class MockRequest:
            class state:
                language = "vi"

        assert get_request_language(MockRequest()) == "vi"


class TestSupportedLanguages:
    """Tests for supported languages constant."""

    def test_expected_languages_present(self):
        """Test that expected languages are supported."""
        expected = {"en", "vi", "es", "fr", "de", "ja", "zh"}
        assert SUPPORTED_LANGUAGES == expected
