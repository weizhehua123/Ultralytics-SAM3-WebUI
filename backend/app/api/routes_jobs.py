from __future__ import annotations

from fastapi import APIRouter, Request

from ..core.errors import http_404
from ..jobs.manager import get_job_manager

router = APIRouter()


@router.get("/{job_id}")
def get_job(job_id: str, request: Request):
    jm = getattr(request.app.state, "job_manager", None) or get_job_manager()
    job = jm.get(job_id)
    if job is None:
        raise http_404("job not found")
    return job.to_dict()
