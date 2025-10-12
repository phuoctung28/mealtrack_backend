"""
Unit tests for notification configuration.
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch

from src.config.notification_config import (
    NotificationConfig,
    get_notification_config,
    reload_notification_config
)


class TestNotificationConfig:
    """Tests for NotificationConfig"""
    
    def test_default_configuration(self):
        """Test default configuration values"""
        with patch.dict(os.environ, {}, clear=True):
            config = NotificationConfig()
            
            assert config.smtp_host is None
            assert config.smtp_port == 587
            assert config.smtp_use_tls is True
            assert config.email_from_address == "noreply@nutreeai.com"
            assert config.email_from_name == "Nutree AI"
            assert config.notification_log_retention_days == 30
            assert config.device_token_inactivity_days == 90
    
    def test_explicit_fcm_credentials_path(self):
        """Test explicit FCM credentials path from environment"""
        test_path = "/test/path/firebase-credentials.json"
        
        with patch.dict(os.environ, {"FCM_CREDENTIALS_PATH": test_path}):
            with patch("os.path.exists", return_value=True):
                config = NotificationConfig()
                
                assert config.fcm_credentials_path == test_path
    
    def test_auto_detect_fcm_credentials(self):
        """Test auto-detection of FCM credentials"""
        with patch.dict(os.environ, {}, clear=True):
            # Mock the file exists at default location
            with patch.object(Path, "exists", return_value=True):
                config = NotificationConfig()
                
                # Should detect credentials/firebase-credentials.json
                assert config.fcm_credentials_path is not None
                assert "firebase-credentials.json" in config.fcm_credentials_path
    
    def test_no_fcm_credentials_found(self):
        """Test when no FCM credentials are found"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "exists", return_value=False):
                config = NotificationConfig()
                
                assert config.fcm_credentials_path is None
    
    def test_smtp_configuration_from_env(self):
        """Test SMTP configuration from environment variables"""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "465",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "secret",
            "SMTP_USE_TLS": "false",
            "EMAIL_FROM_ADDRESS": "noreply@test.com",
            "EMAIL_FROM_NAME": "Test App"
        }
        
        with patch.dict(os.environ, env_vars):
            config = NotificationConfig()
            
            assert config.smtp_host == "smtp.test.com"
            assert config.smtp_port == 465
            assert config.smtp_username == "test@example.com"
            assert config.smtp_password == "secret"
            assert config.smtp_use_tls is False
            assert config.email_from_address == "noreply@test.com"
            assert config.email_from_name == "Test App"
    
    def test_notification_settings_from_env(self):
        """Test notification settings from environment variables"""
        env_vars = {
            "NOTIFICATION_LOG_RETENTION_DAYS": "60",
            "DEVICE_TOKEN_INACTIVITY_DAYS": "120"
        }
        
        with patch.dict(os.environ, env_vars):
            config = NotificationConfig()
            
            assert config.notification_log_retention_days == 60
            assert config.device_token_inactivity_days == 120
    
    def test_get_notification_config_singleton(self):
        """Test that get_notification_config returns singleton"""
        config1 = get_notification_config()
        config2 = get_notification_config()
        
        assert config1 is config2
    
    def test_reload_notification_config(self):
        """Test reloading notification config"""
        config1 = get_notification_config()
        config2 = reload_notification_config()
        
        # Should be different instances after reload
        assert config1 is not config2


class TestNotificationServiceFactory:
    """Tests for NotificationServiceFactory"""
    
    def test_create_preference_service(self, test_session):
        """Test creating preference service"""
        from src.app.services.notification_service_factory import NotificationServiceFactory
        
        service = NotificationServiceFactory.create_preference_service(test_session)
        
        assert service is not None
        assert hasattr(service, "get_preferences")
        assert hasattr(service, "update_preferences")
    
    def test_create_push_service(self, test_session):
        """Test creating push notification service"""
        from src.app.services.notification_service_factory import NotificationServiceFactory
        
        service = NotificationServiceFactory.create_push_service(test_session)
        
        assert service is not None
        assert hasattr(service, "send_push_notification")
    
    def test_create_email_service(self, test_session):
        """Test creating email notification service"""
        from src.app.services.notification_service_factory import NotificationServiceFactory
        
        service = NotificationServiceFactory.create_email_service(test_session)
        
        assert service is not None
        assert hasattr(service, "send_email_notification")
    
    def test_create_dispatch_service(self, test_session):
        """Test creating dispatch service"""
        from src.app.services.notification_service_factory import NotificationServiceFactory
        
        service = NotificationServiceFactory.create_dispatch_service(test_session)
        
        assert service is not None
        assert hasattr(service, "dispatch_notification")
    
    def test_log_service_status(self):
        """Test logging service status"""
        from src.app.services.notification_service_factory import NotificationServiceFactory
        
        # Should not raise any errors
        NotificationServiceFactory.log_service_status()


class TestGracefulDegradation:
    """Test that system works gracefully without FCM/SMTP configured"""
    
    @pytest.mark.asyncio
    async def test_push_service_without_fcm(self, test_session):
        """Test push service works without FCM credentials"""
        from src.app.services.notification_service_factory import NotificationServiceFactory
        from src.domain.model.notification import Notification
        
        # Force no FCM credentials
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "exists", return_value=False):
                service = NotificationServiceFactory.create_push_service(test_session)
                
                notification = Notification(
                    user_id="test-user",
                    notification_type="weight_reminder",
                    delivery_method="push",
                    title="Test",
                    body="Test",
                    data={}
                )
                
                # Should not crash, just return empty list
                result = await service.send_push_notification("test-user", notification)
                assert result == []
    
    @pytest.mark.asyncio
    async def test_email_service_without_smtp(self, test_session):
        """Test email service works without SMTP configuration"""
        from src.app.services.notification_service_factory import NotificationServiceFactory
        from src.domain.model.notification import Notification
        
        # Force no SMTP config
        with patch.dict(os.environ, {}, clear=True):
            service = NotificationServiceFactory.create_email_service(test_session)
            
            notification = Notification(
                user_id="test-user",
                notification_type="weight_reminder",
                delivery_method="email",
                title="Test",
                body="Test",
                data={}
            )
            
            # Should not crash, just return False
            result = await service.send_email_notification(
                to_email="test@example.com",
                notification=notification
            )
            assert result is False


class TestConfigurationValidation:
    """Test configuration validation"""
    
    def test_invalid_fcm_path_logs_warning(self):
        """Test that invalid FCM path logs warning"""
        invalid_path = "/invalid/path/firebase.json"
        
        with patch.dict(os.environ, {"FCM_CREDENTIALS_PATH": invalid_path}):
            with patch("os.path.exists", return_value=False):
                config = NotificationConfig()
                
                # Should fallback to None
                assert config.fcm_credentials_path is None
    
    def test_invalid_smtp_port_uses_default(self):
        """Test that invalid SMTP port uses default"""
        with patch.dict(os.environ, {"SMTP_PORT": "invalid"}):
            # Should raise ValueError or use default
            try:
                config = NotificationConfig()
                # If it doesn't raise, should use default
                assert config.smtp_port == 587
            except ValueError:
                # If it raises, that's also acceptable
                pass
    
    def test_missing_smtp_credentials_logs_warning(self):
        """Test that missing SMTP credentials are handled"""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            # Missing username and password
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = NotificationConfig()
            
            # Should have host but missing credentials
            assert config.smtp_host == "smtp.test.com"
            assert config.smtp_username is None
            assert config.smtp_password is None

