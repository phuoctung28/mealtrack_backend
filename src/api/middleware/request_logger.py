"""
Request/Response logging middleware.
Adds request ID tracking and timing for all API calls.
"""
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.
    
    Features:
    - Generates unique request ID for tracing
    - Logs request method, path, and timing
    - Adds X-Request-ID header to responses
    - Logs slow requests (>1s) at WARNING level
    """

    SLOW_REQUEST_THRESHOLD_SECONDS = 1.0
    
    # Paths to skip logging (health checks, etc.)
    SKIP_PATHS = {
        "/health",
        "/v1/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(self, app: ASGIApp, log_body: bool = False):
        """
        Initialize middleware.
        
        Args:
            app: ASGI application
            log_body: Whether to log request bodies (default False for privacy)
        """
        super().__init__(app)
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Skip logging for excluded paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Generate request ID
        request_id = self._generate_request_id()
        
        # Store in request state for access in handlers
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        self._log_request(request, request_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Log response
            self._log_response(request, response, request_id, elapsed)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            self._log_error(request, request_id, elapsed, e)
            raise

    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return uuid.uuid4().hex[:8]

    def _log_request(self, request: Request, request_id: str) -> None:
        """Log incoming request."""
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get user ID if available
        user_id = self._get_user_id(request)
        user_str = f" user={user_id}" if user_id else ""
        
        logger.info(
            f"[REQ-{request_id}] {request.method} {request.url.path}"
            f" client={client_ip}{user_str}"
        )

    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        elapsed: float,
    ) -> None:
        """Log response details."""
        log_level = logging.INFO
        
        # Warn on slow requests
        if elapsed > self.SLOW_REQUEST_THRESHOLD_SECONDS:
            log_level = logging.WARNING
        
        # Warn on error responses
        if response.status_code >= 400:
            log_level = logging.WARNING
        if response.status_code >= 500:
            log_level = logging.ERROR
        
        logger.log(
            log_level,
            f"[RES-{request_id}] {request.method} {request.url.path}"
            f" status={response.status_code} elapsed={elapsed:.3f}s"
        )

    def _log_error(
        self,
        request: Request,
        request_id: str,
        elapsed: float,
        error: Exception,
    ) -> None:
        """Log error during request processing."""
        logger.error(
            f"[ERR-{request_id}] {request.method} {request.url.path}"
            f" elapsed={elapsed:.3f}s error={type(error).__name__}: {error}"
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check X-Forwarded-For for proxied requests
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"

    def _get_user_id(self, request: Request) -> str | None:
        """Extract user ID from request state if available."""
        try:
            return getattr(request.state, "user_id", None)
        except AttributeError:
            return None


def get_request_id(request: Request) -> str | None:
    """
    Get request ID from request state.
    
    Usage in route handlers:
        @router.get("/example")
        def example(request: Request):
            request_id = get_request_id(request)
            logger.info(f"[{request_id}] Processing example")
    """
    try:
        return getattr(request.state, "request_id", None)
    except AttributeError:
        return None
