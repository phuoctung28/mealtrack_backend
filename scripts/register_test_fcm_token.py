#!/usr/bin/env python3
"""
Script to manually register a test FCM token for a user.
This is useful for testing notifications without needing the mobile app.
"""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infra.database.config import SessionLocal
from src.infra.database.models.notification.user_fcm_token import UserFcmToken as DBUserFcmToken
from src.infra.database.models.user.user import User
from src.infra.database.models.subscription import Subscription  # Import for SQLAlchemy relationships
import uuid


def register_test_token(user_id: str, device_type: str = 'ios'):
    """Register a test FCM token for a user."""
    print(f"\n=== Registering Test FCM Token ===")
    print(f"User ID: {user_id}")
    print(f"Device Type: {device_type}\n")
    
    session = SessionLocal()
    
    try:
        # Check if user exists
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            print(f"❌ ERROR: User {user_id} not found!")
            return False
        
        print(f"✅ User found: {user.email or user.display_name or user.id}")
        
        # Generate a test FCM token (format: test_token_<user_id>_<device>)
        test_token = f"test_fcm_token_{user_id[:8]}_{device_type}_{uuid.uuid4().hex[:8]}"
        
        # Check if token already exists
        existing = session.query(DBUserFcmToken).filter_by(
            user_id=user_id,
            fcm_token=test_token
        ).first()
        
        if existing:
            print(f"⚠️  Token already exists, activating it...")
            existing.is_active = True
            session.commit()
            print(f"✅ Token activated: {existing.id}")
            print(f"   FCM Token: {existing.fcm_token}")
            return True
        
        # Create new token
        new_token = DBUserFcmToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            fcm_token=test_token,
            device_type=device_type,
            is_active=True
        )
        
        session.add(new_token)
        session.commit()
        
        print(f"✅ Test FCM token registered successfully!")
        print(f"   Token ID: {new_token.id}")
        print(f"   FCM Token: {new_token.fcm_token}")
        print(f"   Device: {new_token.device_type}")
        print(f"\n⚠️  NOTE: This is a TEST token. Real notifications won't be delivered.")
        print(f"   But the backend will process them and log the attempts.")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Register a test FCM token for a user')
    parser.add_argument('user_id', help='User ID to register token for')
    parser.add_argument('--device', choices=['ios', 'android'], default='ios', 
                       help='Device type (default: ios)')
    
    args = parser.parse_args()
    
    success = register_test_token(args.user_id, args.device)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

