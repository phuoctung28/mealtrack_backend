"""
Health check endpoints for monitoring and status.
"""

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.infra.database.config import (
    POOL_MAX_OVERFLOW,
    TOTAL_POOL_CAPACITY,
    engine,
)

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint for uptime monitoring.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "message": "API is running",
        },
    )


@router.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "MealTrack API",
        "version": "1.0.0",
        "description": "Meal tracking and nutritional analysis API",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
        },
    }


@router.get("/health/db-pool")
async def database_pool_status():
    """
    Inspect SQLAlchemy connection pool metrics.
    """
    try:
        pool = engine.pool
        checked_out = pool.checkedout()
        pool_size = pool.size()
        overflow = pool.overflow()
        available = max(pool_size - checked_out, 0)
        utilization_pct = (checked_out / pool_size) * 100 if pool_size > 0 else 0.0

        return {
            "status": "healthy",
            "pool_size": pool_size,
            "max_overflow": POOL_MAX_OVERFLOW,
            "checked_out": checked_out,
            "available": available,
            "overflow": overflow,
            "total_capacity": TOTAL_POOL_CAPACITY,
            "utilization_pct": round(utilization_pct, 2),
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(exc),
            },
        )


@router.get("/health/mysql-connections")
async def mysql_connection_status():
    """
    Return active MySQL connection counts for the application.
    """
    try:
        stats = await _fetch_mysql_connection_stats()
        return {
            "status": "healthy",
            **stats,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(exc),
            },
        )


async def _fetch_mysql_connection_stats() -> Dict[str, Any]:
    username = engine.url.username

    def _query() -> Dict[str, Any]:
        with engine.connect() as connection:
            params = {}
            where_clause = ""
            if username:
                where_clause = "WHERE user = :user"
                params["user"] = username

            active_result = connection.execute(
                text(
                    f"SELECT COUNT(*) AS count FROM information_schema.processlist {where_clause}"
                ),
                params,
            )
            active_connections = active_result.scalar_one()

            max_conn_row = connection.execute(
                text("SHOW VARIABLES LIKE 'max_connections'")
            ).fetchone()
            max_connections: Optional[int] = None
            if max_conn_row and len(max_conn_row) > 1:
                try:
                    max_connections = int(max_conn_row[1])
                except (TypeError, ValueError):
                    max_connections = None

            utilization_pct: Optional[float] = None
            if max_connections:
                utilization_pct = (active_connections / max_connections) * 100

            return {
                "active_connections": active_connections,
                "pool_capacity": TOTAL_POOL_CAPACITY,
                "max_connections": max_connections,
                "utilization_pct": (
                    round(utilization_pct, 2) if utilization_pct is not None else None
                ),
            }

    return await asyncio.to_thread(_query)


@router.get("/health/notifications")
async def notification_health_check():
    """
    Health check for push notification system.
    Checks: Firebase SDK init, APNS config status, token stats.
    """
    try:
        from src.infra.services.firebase_service import FirebaseService
        from src.infra.database.config import SessionLocal
        from src.infra.database.models.notification import UserFcmToken as DBToken
        from sqlalchemy import func

        firebase_service = FirebaseService()

        health_status = {
            "status": "healthy",
            "firebase_initialized": firebase_service.is_initialized(),
            "components": {},
        }

        # Check Firebase Admin SDK
        if not firebase_service.is_initialized():
            health_status["status"] = "degraded"
            health_status["components"]["firebase_sdk"] = {
                "status": "error",
                "message": "Firebase Admin SDK not initialized",
            }
        else:
            health_status["components"]["firebase_sdk"] = {
                "status": "healthy",
                "message": "Firebase Admin SDK initialized",
            }

        # Get token stats from database
        db = SessionLocal()
        try:
            total_tokens = db.query(func.count(DBToken.id)).scalar()
            active_tokens = (
                db.query(func.count(DBToken.id)).filter(DBToken.is_active).scalar()
            )
            inactive_tokens = total_tokens - active_tokens

            health_status["components"]["fcm_tokens"] = {
                "status": "healthy",
                "total": total_tokens,
                "active": active_tokens,
                "inactive": inactive_tokens,
                "inactive_rate": (
                    round(inactive_tokens / total_tokens * 100, 2)
                    if total_tokens > 0
                    else 0
                ),
            }

            # Warn if high inactive rate
            if total_tokens > 0 and (inactive_tokens / total_tokens) > 0.5:
                health_status["status"] = "warning"
                health_status["components"]["fcm_tokens"][
                    "message"
                ] = "High inactive token rate"
        finally:
            db.close()

        return JSONResponse(
            status_code=200 if health_status["status"] == "healthy" else 503,
            content=health_status,
        )

    except Exception as e:
        return JSONResponse(
            status_code=503, content={"status": "error", "error": str(e)}
        )
