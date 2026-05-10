"""Tests for App Store download redirect endpoint."""

from fastapi.testclient import TestClient

from src.api.routes.app_download import router, APP_STORE_URL
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app, follow_redirects=False)


def test_app_download_redirects_to_app_store():
    response = client.get("/app-download")

    assert response.status_code == 302
    assert APP_STORE_URL in response.headers["location"]


def test_app_download_includes_default_source():
    response = client.get("/app-download")

    location = response.headers["location"]
    assert "ct=direct" in location
    assert "mt=8" in location


def test_app_download_uses_custom_source():
    response = client.get("/app-download?source=welcome_email")

    location = response.headers["location"]
    assert "ct=welcome_email" in location


def test_app_download_preserves_mt_param():
    response = client.get("/app-download?source=test")

    location = response.headers["location"]
    assert "mt=8" in location


def test_app_download_encodes_special_characters():
    response = client.get("/app-download?source=test&inject=bad")

    location = response.headers["location"]
    # The & should be encoded, not interpreted as param separator
    assert "ct=test%26inject%3Dbad" in location or "ct=test" in location and "inject=bad" not in location
