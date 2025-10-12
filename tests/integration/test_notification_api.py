"""
Integration tests for notification API endpoints.
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile


@pytest.fixture
def api_client(test_session: Session):
    """Create FastAPI test client"""
    from src.api.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers(sample_user: User):
    """Create authentication headers for test user"""
    # Mock authentication - in real app, this would be a JWT token
    return {
        "Authorization": f"Bearer test-token-{sample_user.id}",
        "X-User-ID": sample_user.id  # For testing purposes
    }


class TestNotificationPreferencesAPI:
    """Integration tests for notification preferences endpoints"""
    
    def test_get_notification_preferences(
        self,
        api_client: TestClient,
        sample_user: User,
        sample_user_profile: UserProfile,
        auth_headers: dict
    ):
        """Test GET /api/v1/users/{user_id}/preferences/notifications"""
        response = api_client.get(
            f"/api/v1/users/{sample_user.id}/preferences/notifications",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == sample_user.id
        assert "preferences" in data
        assert "notifications_enabled" in data["preferences"]
    
    def test_update_notification_preferences(
        self,
        api_client: TestClient,
        sample_user: User,
        sample_user_profile: UserProfile,
        auth_headers: dict
    ):
        """Test PUT /api/v1/users/{user_id}/preferences/notifications"""
        update_data = {
            "preferences": {
                "notifications_enabled": True,
                "push_notifications_enabled": False,
                "email_notifications_enabled": True,
                "weekly_weight_reminder_enabled": True,
                "weekly_weight_reminder_day": 1,
                "weekly_weight_reminder_time": "09:00"
            }
        }
        
        response = api_client.put(
            f"/api/v1/users/{sample_user.id}/preferences/notifications",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["preferences"]["push_notifications_enabled"] is False
        assert data["preferences"]["email_notifications_enabled"] is True
        assert data["preferences"]["weekly_weight_reminder_day"] == 1
    
    def test_update_preferences_invalid_day(
        self,
        api_client: TestClient,
        sample_user: User,
        sample_user_profile: UserProfile,
        auth_headers: dict
    ):
        """Test updating preferences with invalid day fails validation"""
        update_data = {
            "preferences": {
                "weekly_weight_reminder_day": 7  # Invalid! Must be 0-6
            }
        }
        
        response = api_client.put(
            f"/api/v1/users/{sample_user.id}/preferences/notifications",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error


class TestDeviceTokenAPI:
    """Integration tests for device token endpoints"""
    
    def test_register_device(
        self,
        api_client: TestClient,
        sample_user: User,
        auth_headers: dict
    ):
        """Test POST /api/v1/users/{user_id}/devices"""
        device_data = {
            "device_token": "fcm-token-abc123",
            "platform": "ios",
            "device_info": {
                "model": "iPhone 14",
                "os": "iOS 17.0"
            }
        }
        
        response = api_client.post(
            f"/api/v1/users/{sample_user.id}/devices",
            json=device_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["device_token"] == "fcm-token-abc123"
        assert data["platform"] == "ios"
        assert data["is_active"] is True
    
    def test_get_user_devices(
        self,
        api_client: TestClient,
        sample_user: User,
        auth_headers: dict
    ):
        """Test GET /api/v1/users/{user_id}/devices"""
        # Register a device first
        device_data = {
            "device_token": "fcm-token-xyz",
            "platform": "android",
            "device_info": {}
        }
        api_client.post(
            f"/api/v1/users/{sample_user.id}/devices",
            json=device_data,
            headers=auth_headers
        )
        
        # Get devices
        response = api_client.get(
            f"/api/v1/users/{sample_user.id}/devices",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        assert len(data["devices"]) >= 1
    
    def test_deactivate_device(
        self,
        api_client: TestClient,
        sample_user: User,
        auth_headers: dict
    ):
        """Test DELETE /api/v1/users/{user_id}/devices/{device_id}"""
        # Register a device first
        device_data = {
            "device_token": "fcm-token-to-delete",
            "platform": "ios",
            "device_info": {}
        }
        register_response = api_client.post(
            f"/api/v1/users/{sample_user.id}/devices",
            json=device_data,
            headers=auth_headers
        )
        device_id = register_response.json()["id"]
        
        # Deactivate device
        response = api_client.delete(
            f"/api/v1/users/{sample_user.id}/devices/{device_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestNotificationHistoryAPI:
    """Integration tests for notification history endpoint"""
    
    def test_get_notification_history(
        self,
        api_client: TestClient,
        sample_user: User,
        auth_headers: dict
    ):
        """Test GET /api/v1/users/{user_id}/notifications/history"""
        response = api_client.get(
            f"/api/v1/users/{sample_user.id}/notifications/history",
            headers=auth_headers,
            params={"limit": 10, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert "total" in data
        assert isinstance(data["notifications"], list)
        assert isinstance(data["total"], int)
    
    def test_get_notification_history_with_filters(
        self,
        api_client: TestClient,
        sample_user: User,
        auth_headers: dict
    ):
        """Test getting notification history with filters"""
        response = api_client.get(
            f"/api/v1/users/{sample_user.id}/notifications/history",
            headers=auth_headers,
            params={
                "limit": 5,
                "offset": 0,
                "notification_type": "weight_reminder"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned notifications should be weight_reminder type
        for notif in data["notifications"]:
            assert notif["notification_type"] == "weight_reminder"


class TestAdminNotificationAPI:
    """Integration tests for admin notification endpoints"""
    
    def test_send_test_notification_without_fcm(
        self,
        api_client: TestClient,
        sample_user: User,
        auth_headers: dict
    ):
        """Test POST /api/v1/admin/users/{user_id}/notifications/test"""
        # Register a device first
        device_data = {
            "device_token": "test-fcm-token",
            "platform": "ios",
            "device_info": {}
        }
        api_client.post(
            f"/api/v1/users/{sample_user.id}/devices",
            json=device_data,
            headers=auth_headers
        )
        
        # Send test notification
        test_data = {
            "notification_type": "weight_reminder",
            "delivery_method": "push"
        }
        
        response = api_client.post(
            f"/api/v1/admin/users/{sample_user.id}/notifications/test",
            json=test_data,
            headers=auth_headers
        )
        
        # Should succeed even without FCM configured (graceful degradation)
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert "notification_ids" in data


class TestAuthorizationChecks:
    """Test authorization for notification endpoints"""
    
    def test_cannot_access_other_user_preferences(
        self,
        api_client: TestClient,
        sample_user: User
    ):
        """Test that users cannot access other users' preferences"""
        # Create headers for a different user
        other_user_id = "different-user-123"
        wrong_headers = {
            "Authorization": f"Bearer test-token-{other_user_id}",
            "X-User-ID": other_user_id
        }
        
        response = api_client.get(
            f"/api/v1/users/{sample_user.id}/preferences/notifications",
            headers=wrong_headers
        )
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_cannot_register_device_for_other_user(
        self,
        api_client: TestClient,
        sample_user: User
    ):
        """Test that users cannot register devices for other users"""
        other_user_id = "different-user-456"
        wrong_headers = {
            "Authorization": f"Bearer test-token-{other_user_id}",
            "X-User-ID": other_user_id
        }
        
        device_data = {
            "device_token": "fcm-token",
            "platform": "ios",
            "device_info": {}
        }
        
        response = api_client.post(
            f"/api/v1/users/{sample_user.id}/devices",
            json=device_data,
            headers=wrong_headers
        )
        
        # Should be forbidden
        assert response.status_code == 403

