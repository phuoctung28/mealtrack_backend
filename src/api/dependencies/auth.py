"""
Authentication dependencies for FastAPI.

Provides Firebase token verification and user extraction.
"""

import logging
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from sqlalchemy.orm import Session

from src.infra.database.config import get_db

logger = logging.getLogger(__name__)

# Security scheme for OpenAPI documentation (auto_error=False for dev bypass)
security = HTTPBearer(auto_error=False)


async def verify_firebase_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Verify Firebase ID token and return decoded token.

    In development mode (ENVIRONMENT=development), bypasses Firebase verification
    and uses the dev user injected by middleware.

    This dependency extracts and verifies the Firebase ID token from the
    Authorization header. It should be used as a dependency for all
    protected endpoints.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token credentials (optional in dev mode)

    Returns:
        Decoded Firebase token containing user information

    Raises:
        HTTPException: If token is invalid, expired, or revoked

    Example:
        @router.get("/protected")
        async def protected_endpoint(
            token: dict = Depends(verify_firebase_token)
        ):
            user_id = token['uid']
            return {"message": f"Hello {user_id}"}
    """
    # Dev mode bypass: check if dev middleware injected a user
    if os.getenv("ENVIRONMENT") == "development" and hasattr(request.state, "user"):
        dev_user = request.state.user
        logger.debug("Dev mode: bypassing Firebase auth, using dev user: %s", dev_user.id)
        return {
            "uid": dev_user.firebase_uid,
            "email": dev_user.email,
            "sub": dev_user.firebase_uid
        }

    # Production mode: require Firebase token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Verify the Firebase ID token
        decoded_token = firebase_auth.verify_id_token(token)
        logger.debug(
            "Successfully verified token for user: %s", decoded_token.get("uid")
        )
        return decoded_token

    except firebase_auth.ExpiredIdTokenError as e:
        logger.warning("Expired Firebase token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except firebase_auth.RevokedIdTokenError as e:
        logger.warning("Revoked Firebase token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except firebase_auth.InvalidIdTokenError as e:
        logger.warning("Invalid Firebase token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except firebase_auth.CertificateFetchError as e:
        logger.error("Failed to fetch Firebase certificates: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from e
    except Exception as e:
        logger.error("Unexpected error verifying Firebase token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to verify authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_id(
    token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db)
) -> str:
    """
    Extract the authenticated user's database ID from the verified Firebase token.

    This dependency:
    1. Extracts the Firebase UID from the verified token
    2. Looks up the user in the database by firebase_uid
    3. Returns the database user.id (UUID primary key)

    This ensures that the user_id matches what's expected by all database queries.

    Args:
        token: Verified Firebase token (injected by verify_firebase_token)
        db: Database session (injected by get_db)

    Returns:
        The authenticated user's database ID (UUID)

    Raises:
        HTTPException: If token is invalid or user not found in database

    Example:
        @router.get("/profile")
        async def get_profile(
            user_id: str = Depends(get_current_user_id)
        ):
            return {"user_id": user_id}
    """
    firebase_uid = token.get("uid")
    if not firebase_uid:
        logger.error("Firebase token missing 'uid' field")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user identifier",
        )
    
    # Look up user in database by firebase_uid (only active users)
    from src.infra.database.models.user.user import User
    user = db.query(User).filter(
        User.firebase_uid == firebase_uid,
        User.is_active == True  # CRITICAL: Block deleted/inactive users from authenticating
    ).first()

    if not user:
        logger.warning("Active user with Firebase UID not found in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "USER_NOT_FOUND",
                "message": "User not found or account has been deleted.",
                "details": {
                    "hint": "If your account was deleted, you cannot log in. If you're a new user, call POST /v1/users/sync to create your account."
                }
            }
        )
    
    return user.id


async def get_current_user_email(
    token: dict = Depends(verify_firebase_token),
) -> Optional[str]:
    """
    Extract the authenticated user's email from the verified Firebase token.

    Args:
        token: Verified Firebase token (injected by verify_firebase_token)

    Returns:
        The authenticated user's email, or None if not available
    """
    return token.get("email")


async def optional_authentication(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    """
    Optional authentication dependency for endpoints that work with or without auth.

    Returns None if no credentials provided, otherwise verifies and returns token.

    Args:
        credentials: Optional HTTP Bearer token credentials

    Returns:
        Decoded Firebase token if credentials provided, None otherwise

    Example:
        @router.get("/public-or-private")
        async def endpoint(
            token: Optional[dict] = Depends(optional_authentication)
        ):
            if token:
                return {"message": "Authenticated", "user_id": token['uid']}
            else:
                return {"message": "Anonymous"}
    """
    if not credentials:
        return None

    try:
        decoded_token = firebase_auth.verify_id_token(credentials.credentials)
        return decoded_token
    except Exception as e:
        logger.debug("Optional auth failed: %s", str(e))
        return None
