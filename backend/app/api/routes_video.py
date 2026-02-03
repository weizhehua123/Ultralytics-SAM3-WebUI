from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, File, Form, UploadFile

from ..core.errors import http_400
from ..jobs.manager import get_job_manager
from ..services.io import save_upload_file

router = APIRouter()


@router.post("/track/bbox")
async def track_bbox(video: UploadFile = File(...), init_bboxes_json: str = Form(...)):
    try:
        bboxes = json.loads(init_bboxes_json)
    except Exception:
        raise http_400("init_bboxes_json must be valid JSON")
    jm = get_job_manager()
    job_id = uuid.uuid4().hex
    job_dir = jm.job_dir(job_id)
    in_path = job_dir / "input" / "video" / (video.filename or "video.mp4")
    save_upload_file(video, in_path)
    job = jm.create_with_id(job_id=job_id, job_type="video_bbox", payload={"video_path": str(in_path), "bboxes": bboxes})
    return {"job_id": job.id, "status": job.status}


@router.post("/track/text")
async def track_text(video: UploadFile = File(...), prompt: str = Form(...)):
    if not prompt or not prompt.strip():
        raise http_400("prompt is required")
    jm = get_job_manager()
    job_id = uuid.uuid4().hex
    job_dir = jm.job_dir(job_id)
    in_path = job_dir / "input" / "video" / (video.filename or "video.mp4")
    save_upload_file(video, in_path)
    job = jm.create_with_id(job_id=job_id, job_type="video_text", payload={"video_path": str(in_path), "prompt": prompt})
    return {"job_id": job.id, "status": job.status}
