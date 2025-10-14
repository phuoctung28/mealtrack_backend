"""
Repository for notification-related database operations.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_

from src.infra.database.models.notification.device_token import DeviceToken
from src.infra.database.models.notification.notification_log import NotificationLog
from src.domain.model.notification import Notification


class DeviceTokenRepository:
    """Repository for device token operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: str,
        device_token: str,
        platform: str,
        device_info: dict
    ) -> DeviceToken:
        """Create a new device token"""
        token = DeviceToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            device_token=device_token,
            platform=platform,
            device_info=device_info,
            is_active=True,
            last_used_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token
    
    async def get_by_id(self, token_id: str) -> Optional[DeviceToken]:
        """Get device token by ID"""
        result = await self.session.execute(
            select(DeviceToken).where(DeviceToken.id == token_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_token(self, device_token: str) -> Optional[DeviceToken]:
        """Get device token by token string"""
        result = await self.session.execute(
            select(DeviceToken).where(DeviceToken.device_token == device_token)
        )
        return result.scalar_one_or_none()
    
    async def get_active_devices(self, user_id: str) -> List[DeviceToken]:
        """Get all active devices for a user"""
        result = await self.session.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.is_active == True
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_all_user_devices(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[DeviceToken]:
        """Get all devices for a user"""
        query = select(DeviceToken).where(DeviceToken.user_id == user_id)
        
        if active_only:
            query = query.where(DeviceToken.is_active == True)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_last_used(self, token_id: str) -> None:
        """Update last used timestamp"""
        await self.session.execute(
            update(DeviceToken)
            .where(DeviceToken.id == token_id)
            .values(
                last_used_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
    
    async def mark_inactive(self, token_id: str) -> None:
        """Mark device token as inactive"""
        await self.session.execute(
            update(DeviceToken)
            .where(DeviceToken.id == token_id)
            .values(
                is_active=False,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
    
    async def delete_by_id(self, token_id: str) -> bool:
        """Delete device token by ID"""
        result = await self.session.execute(
            delete(DeviceToken).where(DeviceToken.id == token_id)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def delete_by_user(self, user_id: str) -> int:
        """Delete all device tokens for a user"""
        result = await self.session.execute(
            delete(DeviceToken).where(DeviceToken.user_id == user_id)
        )
        await self.session.commit()
        return result.rowcount


class NotificationLogRepository:
    """Repository for notification log operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_log(
        self,
        user_id: str,
        notification: Notification,
        device_token_id: Optional[str] = None
    ) -> str:
        """Create a new notification log"""
        log = NotificationLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            notification_type=notification.notification_type,
            delivery_method=notification.delivery_method,
            title=notification.title,
            body=notification.body,
            data=notification.data,
            status='pending',
            device_token_id=device_token_id,
            error_message=None,
            sent_at=None,
            delivered_at=None,
            opened_at=None,
            created_at=datetime.utcnow()
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log.id
    
    async def get_by_id(self, log_id: str) -> Optional[NotificationLog]:
        """Get notification log by ID"""
        result = await self.session.execute(
            select(NotificationLog).where(NotificationLog.id == log_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_logs(
        self,
        user_id: str,
        notification_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[NotificationLog], int]:
        """Get notification logs for a user with pagination"""
        # Build base query
        query = select(NotificationLog).where(NotificationLog.user_id == user_id)
        
        if notification_type:
            query = query.where(NotificationLog.notification_type == notification_type)
        
        # Get total count
        count_query = select(NotificationLog).where(NotificationLog.user_id == user_id)
        if notification_type:
            count_query = count_query.where(NotificationLog.notification_type == notification_type)
        
        count_result = await self.session.execute(count_query)
        total = len(list(count_result.scalars().all()))
        
        # Get paginated results
        query = query.order_by(NotificationLog.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        logs = list(result.scalars().all())
        
        return logs, total
    
    async def update_status(
        self,
        log_id: str,
        status: str,
        sent_at: Optional[datetime] = None,
        delivered_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update notification log status"""
        values = {'status': status}
        
        if sent_at:
            values['sent_at'] = sent_at
        if delivered_at:
            values['delivered_at'] = delivered_at
        if error_message:
            values['error_message'] = error_message
        
        await self.session.execute(
            update(NotificationLog)
            .where(NotificationLog.id == log_id)
            .values(**values)
        )
        await self.session.commit()
    
    async def mark_opened(self, log_id: str, opened_at: datetime) -> None:
        """Mark notification as opened"""
        await self.session.execute(
            update(NotificationLog)
            .where(NotificationLog.id == log_id)
            .values(
                status='opened',
                opened_at=opened_at
            )
        )
        await self.session.commit()
    
    async def delete_old_logs(self, days: int) -> int:
        """Delete notification logs older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            delete(NotificationLog).where(NotificationLog.created_at < cutoff_date)
        )
        await self.session.commit()
        return result.rowcount


from datetime import timedelta

