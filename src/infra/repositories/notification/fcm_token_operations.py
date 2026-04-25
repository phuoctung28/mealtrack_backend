"""FCM token CRUD operations."""

import logging
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.domain.model.notification import UserFcmToken
from src.infra.database.models.notification import UserFcmTokenORM
from src.infra.mappers.notification_mapper import fcm_token_orm_to_domain

logger = logging.getLogger(__name__)


class FcmTokenOperations:
    """Handles FCM token database operations."""

    @staticmethod
    def save_fcm_token(db: Session, token: UserFcmToken) -> UserFcmToken:
        """Save an FCM token to the database."""
        try:
            existing_token = (
                db.query(UserFcmTokenORM)
                .filter(UserFcmTokenORM.fcm_token == token.fcm_token)
                .first()
            )

            if existing_token:
                existing_token.user_id = token.user_id
                existing_token.device_type = token.device_type.value
                existing_token.is_active = token.is_active
                existing_token.updated_at = token.updated_at
                db.commit()
                return fcm_token_orm_to_domain(existing_token)
            else:
                db_token = UserFcmTokenORM(
                    id=token.token_id,
                    user_id=token.user_id,
                    fcm_token=token.fcm_token,
                    device_type=token.device_type.value,
                    is_active=token.is_active,
                    created_at=token.created_at,
                    updated_at=token.updated_at,
                )
                db.add(db_token)
                db.commit()
                return fcm_token_orm_to_domain(db_token)
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving FCM token: {e}")
            raise e

    @staticmethod
    def find_fcm_token_by_token(db: Session, fcm_token: str) -> Optional[UserFcmToken]:
        """Find an FCM token by the token string."""
        db_token = (
            db.query(UserFcmTokenORM)
            .filter(UserFcmTokenORM.fcm_token == fcm_token)
            .first()
        )
        return fcm_token_orm_to_domain(db_token) if db_token else None

    @staticmethod
    def find_active_fcm_tokens_by_user(db: Session, user_id: str) -> List[UserFcmToken]:
        """Find all active FCM tokens for a user."""
        db_tokens = (
            db.query(UserFcmTokenORM)
            .filter(
                and_(
                    UserFcmTokenORM.user_id == user_id,
                    UserFcmTokenORM.is_active == True,
                )
            )
            .all()
        )
        return [fcm_token_orm_to_domain(token) for token in db_tokens]

    @staticmethod
    def deactivate_fcm_token(db: Session, fcm_token: str) -> bool:
        """Deactivate an FCM token."""
        try:
            db_token = (
                db.query(UserFcmTokenORM)
                .filter(UserFcmTokenORM.fcm_token == fcm_token)
                .first()
            )

            if db_token:
                db_token.is_active = False
                db.commit()
                return True
            else:
                return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deactivating FCM token: {e}")
            raise e

    @staticmethod
    def delete_fcm_token(db: Session, fcm_token: str) -> bool:
        """Delete an FCM token."""
        try:
            db_token = (
                db.query(UserFcmTokenORM)
                .filter(UserFcmTokenORM.fcm_token == fcm_token)
                .first()
            )

            if db_token:
                db.delete(db_token)
                db.commit()
                return True
            else:
                return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting FCM token: {e}")
            raise e
