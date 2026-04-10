"""
Health check endpoints for monitoring and status.
"""

import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.infra.database.config import (
    IS_NEON_POOLER,
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
    When using NullPool (Neon pooler), pool metrics are not available.
    """
    if IS_NEON_POOLER:
        return {
            "status": "healthy",
            "pool_type": "NullPool",
            "note": "Neon pooler (PgBouncer) handles connection reuse",
        }

    try:
        pool = engine.pool
        checked_out = pool.checkedout()
        pool_size = pool.size()
        overflow = pool.overflow()
        available = max(pool_size - checked_out, 0)
        utilization_pct = (checked_out / pool_size) * 100 if pool_size > 0 else 0.0

        return {
            "status": "healthy",
            "pool_type": "QueuePool",
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
            content={"status": "error", "error": str(exc)},
        )


@router.get("/health/db-connections")
async def db_connection_status():
    """
    Return active PostgreSQL connection counts.
    """
    try:
        stats = await _fetch_pg_connection_stats()
        return {"status": "healthy", **stats}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": str(exc)},
        )


async def _fetch_pg_connection_stats() -> Dict[str, Any]:
    db_name = engine.url.database

    def _query() -> Dict[str, Any]:
        with engine.connect() as connection:
            # pg_stat_activity works through PgBouncer (it's a regular SELECT)
            active_result = connection.execute(
                text(
                    "SELECT COUNT(*) FROM pg_stat_activity "
                    "WHERE datname = :db_name AND state IS NOT NULL"
                ),
                {"db_name": db_name},
            )
            active_connections = active_result.scalar_one()

            # SHOW commands may fail through PgBouncer in transaction mode
            max_connections: Optional[int] = None
            try:
                max_conn_row = connection.execute(
                    text("SHOW max_connections")
                ).fetchone()
                if max_conn_row:
                    max_connections = int(max_conn_row[0])
            except Exception:
                pass

            utilization_pct: Optional[float] = None
            if max_connections:
                utilization_pct = (active_connections / max_connections) * 100

            return {
                "active_connections": active_connections,
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
