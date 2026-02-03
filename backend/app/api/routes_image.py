from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, File, Form, UploadFile

from ..core.errors import http_400
from ..jobs.manager import get_job_manager
from ..services.io import save_upload_file

router = APIRouter()


@router.post("/segment/text")
async def segment_text(image: UploadFile = File(...), prompt: str = Form(...)):
    if not prompt or not prompt.strip():
        raise http_400("prompt is required")
    jm = get_job_manager()
    job_id = uuid.uuid4().hex
    job_dir = jm.job_dir(job_id)
    in_path = job_dir / "input" / "image" / (image.filename or "image")
    save_upload_file(image, in_path)
    job = jm.create_with_id(job_id=job_id, job_type="image_text", payload={"image_path": str(in_path), "prompt": prompt})
    return {"job_id": job.id, "status": job.status}


@router.post("/segment/exemplar")
async def segment_exemplar(image: UploadFile = File(...), bboxes_json: str = Form(...)):
    try:
        bboxes = json.loads(bboxes_json)
    except Exception:
        raise http_400("bboxes_json must be valid JSON")
    jm = get_job_manager()
    job_id = uuid.uuid4().hex
    job_dir = jm.job_dir(job_id)
    in_path = job_dir / "input" / "image" / (image.filename or "image")
    save_upload_file(image, in_path)
    job = jm.create_with_id(
        job_id=job_id,
        job_type="image_exemplar",
        payload={"image_path": str(in_path), "bboxes": bboxes},
    )
    return {"job_id": job.id, "status": job.status}


@router.post("/embedding")
async def create_embedding(image: UploadFile = File(...), ttl_sec: int = Form(1800)):
    jm = get_job_manager()
    job_id = uuid.uuid4().hex
    job_dir = jm.job_dir(job_id)
    in_path = job_dir / "input" / "image" / (image.filename or "image")
    save_upload_file(image, in_path)
    job = jm.create_with_id(
        job_id=job_id,
        job_type="embedding_create",
        payload={"image_path": str(in_path), "ttl_sec": int(ttl_sec)},
    )
    return {"job_id": job.id, "status": job.status}


@router.post("/query")
async def query_embedding(payload: dict):
    embedding_id = payload.get("embedding_id")
    query = payload.get("query")
    if not embedding_id or not isinstance(query, dict):
        raise http_400("payload must contain embedding_id and query")
    jm = get_job_manager()
    job_id = uuid.uuid4().hex
    job = jm.create_with_id(
        job_id=job_id,
        job_type="embedding_query",
        payload={"embedding_id": embedding_id, "query": query},
    )
    return {"job_id": job.id, "status": job.status}
