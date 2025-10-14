"""
Unit tests for notification repositories.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.infra.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationLogRepository
)
from src.infra.database.models.notification.device_token import DeviceToken as DeviceTokenModel
from src.infra.database.models.notification.notification_log import NotificationLog as NotificationLogModel
from src.infra.database.models.user.user import User


@pytest.mark.asyncio
class TestDeviceTokenRepository:
    """Tests for DeviceTokenRepository"""
    
    async def test_register_new_device(self, test_session: Session, sample_user: User):
        """Test registering a new device token"""
        repo = DeviceTokenRepository(test_session)
        
        device_token = await repo.register_device(
            user_id=sample_user.id,
            device_token="fcm-token-123",
            platform="ios",
            device_info={"model": "iPhone 14", "os": "iOS 17"}
        )
        
        assert device_token is not None
        assert device_token.user_id == sample_user.id
        assert device_token.device_token == "fcm-token-123"
        assert device_token.platform == "ios"
        assert device_token.is_active is True
    
    async def test_register_existing_device_updates_timestamp(
        self, test_session: Session, sample_user: User
    ):
        """Test registering existing device updates last_used_at"""
        repo = DeviceTokenRepository(test_session)
        
        # Register device first time
        first_token = await repo.register_device(
            user_id=sample_user.id,
            device_token="fcm-token-existing",
            platform="android",
            device_info={"model": "Pixel 7"}
        )
        first_used = first_token.last_used_at
        
        # Wait a moment
        import asyncio
        await asyncio.sleep(0.1)
        
        # Register same device again
        second_token = await repo.register_device(
            user_id=sample_user.id,
            device_token="fcm-token-existing",
            platform="android",
            device_info={"model": "Pixel 7"}
        )
        
        assert second_token.id == first_token.id
        assert second_token.last_used_at > first_used
    
    async def test_get_active_devices_for_user(
        self, test_session: Session, sample_user: User
    ):
        """Test getting active devices for user"""
        repo = DeviceTokenRepository(test_session)
        
        # Register multiple devices
        await repo.register_device(
            user_id=sample_user.id,
            device_token="fcm-token-1",
            platform="ios",
            device_info={}
        )
        await repo.register_device(
            user_id=sample_user.id,
            device_token="fcm-token-2",
            platform="android",
            device_info={}
        )
        
        # Get active devices
        devices = await repo.get_active_devices_for_user(sample_user.id)
        
        assert len(devices) == 2
        assert all(d.is_active for d in devices)
    
    async def test_deactivate_device(self, test_session: Session, sample_user: User):
        """Test deactivating a device"""
        repo = DeviceTokenRepository(test_session)
        
        # Register device
        device = await repo.register_device(
            user_id=sample_user.id,
            device_token="fcm-token-to-deactivate",
            platform="ios",
            device_info={}
        )
        
        # Deactivate device
        success = await repo.deactivate_device(sample_user.id, device.id)
        
        assert success is True
        
        # Verify device is deactivated
        updated_device = await repo.get_device_by_id(device.id)
        assert updated_device.is_active is False
    
    async def test_cleanup_inactive_devices(self, test_session: Session, sample_user: User):
        """Test cleaning up inactive devices"""
        repo = DeviceTokenRepository(test_session)
        
        # Create old device
        old_device = DeviceTokenModel(
            user_id=sample_user.id,
            device_token="old-token",
            platform="ios",
            device_info={},
            is_active=True,
            last_used_at=datetime.now() - timedelta(days=100),
            created_at=datetime.now() - timedelta(days=100),
            updated_at=datetime.now() - timedelta(days=100)
        )
        test_session.add(old_device)
        test_session.commit()
        
        # Cleanup devices older than 90 days
        deleted_count = await repo.cleanup_inactive_devices(days=90)
        
        assert deleted_count == 1


@pytest.mark.asyncio
class TestNotificationLogRepository:
    """Tests for NotificationLogRepository"""
    
    async def test_create_log(self, test_session: Session, sample_user: User):
        """Test creating a notification log"""
        repo = NotificationLogRepository(test_session)
        
        log = await repo.create_log(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="push",
            title="Test Notification",
            body="Test body",
            data={"test": True},
            device_token_id="device-123"
        )
        
        assert log is not None
        assert log.user_id == sample_user.id
        assert log.notification_type == "weight_reminder"
        assert log.status == "pending"
    
    async def test_mark_sent(self, test_session: Session, sample_user: User):
        """Test marking notification as sent"""
        repo = NotificationLogRepository(test_session)
        
        # Create log
        log = await repo.create_log(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="push",
            title="Test",
            body="Test",
            data={},
            device_token_id="device-123"
        )
        
        # Mark as sent
        success = await repo.mark_sent(log.id)
        
        assert success is True
        
        # Verify status
        updated_log = await repo.get_log_by_id(log.id)
        assert updated_log.status == "sent"
        assert updated_log.sent_at is not None
    
    async def test_mark_failed(self, test_session: Session, sample_user: User):
        """Test marking notification as failed"""
        repo = NotificationLogRepository(test_session)
        
        # Create log
        log = await repo.create_log(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="push",
            title="Test",
            body="Test",
            data={},
            device_token_id="device-123"
        )
        
        # Mark as failed
        success = await repo.mark_failed(log.id, "Device token invalid")
        
        assert success is True
        
        # Verify status
        updated_log = await repo.get_log_by_id(log.id)
        assert updated_log.status == "failed"
        assert updated_log.error_message == "Device token invalid"
    
    async def test_get_user_notification_history(
        self, test_session: Session, sample_user: User
    ):
        """Test getting user notification history"""
        repo = NotificationLogRepository(test_session)
        
        # Create multiple logs
        for i in range(5):
            await repo.create_log(
                user_id=sample_user.id,
                notification_type="weight_reminder",
                delivery_method="push",
                title=f"Notification {i}",
                body="Test",
                data={},
                device_token_id=f"device-{i}"
            )
        
        # Get history with pagination
        logs, total = await repo.get_user_notification_history(
            user_id=sample_user.id,
            limit=3,
            offset=0
        )
        
        assert len(logs) == 3
        assert total == 5
    
    async def test_cleanup_old_logs(self, test_session: Session, sample_user: User):
        """Test cleaning up old notification logs"""
        repo = NotificationLogRepository(test_session)
        
        # Create old log
        old_log = NotificationLogModel(
            user_id=sample_user.id,
            notification_type="weight_reminder",
            delivery_method="push",
            title="Old Notification",
            body="Test",
            data={},
            status="sent",
            device_token_id="device-123",
            created_at=datetime.now() - timedelta(days=40)
        )
        test_session.add(old_log)
        test_session.commit()
        
        # Cleanup logs older than 30 days
        deleted_count = await repo.cleanup_old_logs(days=30)
        
        assert deleted_count == 1

