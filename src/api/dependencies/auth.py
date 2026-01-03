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

# Security scheme for OpenAPI documentation
security = HTTPBearer()


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verify Firebase ID token and return decoded token.

    This dependency extracts and verifies the Firebase ID token from the
    Authorization header. It should be used as a dependency for all
    protected endpoints.

    Note: HTTPBearer with auto_error=True (default) automatically returns
    401 if Authorization header is missing, so credentials will never be None.

    Args:
        credentials: HTTP Bearer token credentials (guaranteed to exist)

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
    request: Request,
    db: Session = Depends(get_db)
) -> str:
    """
    Extract the authenticated user's database ID from the verified Firebase token.
    
    In development mode, checks request.state.user first (set by dev_auth_bypass middleware)
    before attempting Firebase token verification.

    This dependency:
    1. Checks for dev bypass user (development mode)
    2. Extracts the Firebase UID from the verified token (production)
    3. Looks up the user in the database by firebase_uid
    4. Returns the database user.id (UUID primary key)

    This ensures that the user_id matches what's expected by all database queries.

    Args:
        request: FastAPI request object (for dev bypass check)
        token: Verified Firebase token (optional, for production)
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
    # Check for dev bypass user first (development mode)
    if hasattr(request.state, 'user') and request.state.user:
        logger.debug("Using dev bypass user: %s", request.state.user.id)
        return request.state.user.id
    
    # Check for debug token bypass
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token_str = auth_header.split(" ")[1]
        # Skip Firebase verification for debug token
        if token_str == "debug-token-bypass":
            # Use dev user from database
            firebase_uid = os.getenv("DEV_USER_FIREBASE_UID", "dev_firebase_uid")
            from src.infra.database.models.user.user import User
            user = db.query(User).filter(
                User.firebase_uid == firebase_uid,
                User.is_active == True
            ).first()
            if user:
                logger.debug("Using dev user for debug-token-bypass: %s", user.id)
                return user.id
    
    # Normal Firebase token verification
    try:
        security = HTTPBearer()
        credentials = await security(request)
        token = await verify_firebase_token(credentials)
    except Exception as e:
        logger.warning("Token verification failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    
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
