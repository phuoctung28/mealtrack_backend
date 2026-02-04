"""Task status endpoints for RQ jobs."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from rq.job import Job

from src.api.dependencies.auth import optional_authentication
from src.api.schemas.response.task_responses import TaskStatusResponse
from src.infra.rq.redis_connection import get_rq_redis_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tasks", tags=["Tasks"])


def _map_rq_status(rq_status: str) -> str:
    # RQ statuses: queued, started, finished, failed, deferred, scheduled, stopped, canceled
    return {
        "queued": "pending",
        "deferred": "pending",
        "scheduled": "pending",
        "started": "processing",
        "finished": "completed",
        "failed": "failed",
        "canceled": "canceled",
        "stopped": "failed",
    }.get(rq_status, rq_status)


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    token: dict | None = Depends(optional_authentication),
):
    """Poll status/result for an async background task."""
    try:
        redis_conn = get_rq_redis_connection()
        job = Job.fetch(task_id, connection=redis_conn)

        job_user_id = (job.meta or {}).get("user_id")
        if job_user_id:
            # Job is bound to an authenticated user_id (database ID).
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
                )
            from src.api.dependencies.auth import get_current_user_id

            current_user_id = await get_current_user_id(token=token)
            if job_user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
                )

        rq_status = job.get_status(refresh=True)
        return TaskStatusResponse(
            task_id=task_id,
            status=_map_rq_status(rq_status),
            result=job.result if job.is_finished else None,
            error=job.exc_info if job.is_failed else None,
            created_at=job.created_at,
            completed_at=job.ended_at,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Error fetching task %s: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        ) from exc

