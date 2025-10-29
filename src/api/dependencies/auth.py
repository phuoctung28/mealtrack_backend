"""
Authentication dependencies for FastAPI.

Provides Firebase token verification and user extraction.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth

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


async def get_current_user_id(token: dict = Depends(verify_firebase_token)) -> str:
    """
    Extract the authenticated user's ID from the verified Firebase token.

    This is a convenience dependency that extracts just the user ID
    from the verified token. Use this when you only need the user ID.

    Args:
        token: Verified Firebase token (injected by verify_firebase_token)

    Returns:
        The authenticated user's Firebase UID

    Example:
        @router.get("/profile")
        async def get_profile(
            user_id: str = Depends(get_current_user_id)
        ):
            return {"user_id": user_id}
    """
    user_id = token.get("uid")
    if not user_id:
        logger.error("Firebase token missing 'uid' field")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user identifier",
        )
    return user_id


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
