"""
Integration tests for Uploads API endpoints.
"""

import pytest


@pytest.mark.integration
@pytest.mark.api
class TestUploadsAPI:
    """Integration tests for uploads signing endpoint."""

    def test_sign_upload_success(self, authenticated_client):
        response = authenticated_client.post("/v1/uploads/sign")

        assert response.status_code == 200
        data = response.json()
        assert data["timestamp"] is not None
        assert data["signature"] == "mock_signature"
        assert data["api_key"] == "mock_api_key"
        assert data["cloud_name"] == "mock_cloud"
        assert data["public_id"].startswith("mealtrack/")
        assert data["folder"] == "mealtrack"
