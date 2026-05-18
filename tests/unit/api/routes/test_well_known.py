"""Tests for Apple App Site Association endpoint."""

from fastapi.testclient import TestClient

from src.api.routes.well_known import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_aasa_returns_json():
    response = client.get("/.well-known/apple-app-site-association")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_aasa_has_applinks_structure():
    response = client.get("/.well-known/apple-app-site-association")
    data = response.json()

    assert "applinks" in data
    assert "apps" in data["applinks"]
    assert "details" in data["applinks"]
    assert data["applinks"]["apps"] == []


def test_aasa_has_correct_paths():
    response = client.get("/.well-known/apple-app-site-association")
    data = response.json()

    details = data["applinks"]["details"][0]
    expected_paths = [
        "/log", "/log/*",
        "/dashboard", "/dashboard/*",
        "/upgrade", "/upgrade/*",
        "/feedback", "/feedback/*",
        "/settings/*"
    ]

    assert details["paths"] == expected_paths


def test_aasa_has_app_id():
    response = client.get("/.well-known/apple-app-site-association")
    data = response.json()

    details = data["applinks"]["details"][0]
    assert "appID" in details
    assert ".com.nutreeai.mobile" in details["appID"]
