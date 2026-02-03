from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from ..services.embedding_cache import CachedEmbedding, get_embedding_cache
from ..services.sam3 import get_sam3_services
from .models import Job, JobError, JobResult


def _files_url(rel_path_under_results_dir: str) -> str:
    # /files is mounted to settings.results_dir
    return f"/files/{rel_path_under_results_dir.strip('/')}"


def _save_mask_png(mask: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray((mask.astype(np.uint8) * 255))
    img.save(out_path)


def handle_image_text(job: Job, jm) -> None:
    job_dir = jm.job_dir(job.id)
    input_path = Path(job.payload["image_path"])
    prompt = str(job.payload["prompt"]).strip()

    if not prompt:
        job.status = "failed"
        job.error = JobError(message="empty prompt")
        jm.persist(job)
        return

    im = cv2.imread(str(input_path))
    if im is None:
        raise RuntimeError(f"failed to read image: {input_path}")

    services = get_sam3_services()
    predictor = services.get_semantic_predictor()
    predictor.set_image(im)

    results = predictor(text=[prompt])
    r0 = results[0] if isinstance(results, (list, tuple)) and results else results

    out_rel_dir = f"jobs/{job.id}"
    out_dir = jm.results_dir / out_rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    overlay_path = out_dir / "overlay.png"
    masks_dir = out_dir / "masks"

    overlay = None
    if hasattr(r0, "plot"):
        overlay = r0.plot()
        cv2.imwrite(str(overlay_path), overlay)

    masks_saved = []
    if hasattr(r0, "masks") and getattr(r0, "masks") is not None and hasattr(r0.masks, "data"):
        masks = r0.masks.data
        masks_np = masks.detach().cpu().numpy()
        for i, m in enumerate(masks_np):
            p = masks_dir / f"mask_{i:03d}.png"
            _save_mask_png(m, p)
            masks_saved.append(_files_url(f"{out_rel_dir}/masks/{p.name}"))

    job.result = JobResult(
        files={
            "overlay": _files_url(f"{out_rel_dir}/overlay.png") if overlay_path.exists() else "",
            "masks": masks_saved,
        },
        meta={"prompt": prompt, "num_masks": len(masks_saved)},
    )
    jm.persist(job)


def handle_image_exemplar(job: Job, jm) -> None:
    input_path = Path(job.payload["image_path"])
    bboxes = job.payload["bboxes"]

    im = cv2.imread(str(input_path))
    if im is None:
        raise RuntimeError(f"failed to read image: {input_path}")

    services = get_sam3_services()
    predictor = services.get_semantic_predictor()
    predictor.set_image(im)

    results = predictor(bboxes=bboxes)
    r0 = results[0] if isinstance(results, (list, tuple)) and results else results

    out_rel_dir = f"jobs/{job.id}"
    out_dir = jm.results_dir / out_rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    overlay_path = out_dir / "overlay.png"
    masks_dir = out_dir / "masks"

    if hasattr(r0, "plot"):
        cv2.imwrite(str(overlay_path), r0.plot())

    masks_saved = []
    if hasattr(r0, "masks") and getattr(r0, "masks") is not None and hasattr(r0.masks, "data"):
        masks_np = r0.masks.data.detach().cpu().numpy()
        for i, m in enumerate(masks_np):
            p = masks_dir / f"mask_{i:03d}.png"
            _save_mask_png(m, p)
            masks_saved.append(_files_url(f"{out_rel_dir}/masks/{p.name}"))

    job.result = JobResult(
        files={
            "overlay": _files_url(f"{out_rel_dir}/overlay.png") if overlay_path.exists() else "",
            "masks": masks_saved,
        },
        meta={"bboxes": bboxes, "num_masks": len(masks_saved)},
    )
    jm.persist(job)


def handle_embedding_create(job: Job, jm) -> None:
    input_path = Path(job.payload["image_path"])
    ttl_sec = int(job.payload.get("ttl_sec", 1800))

    im = cv2.imread(str(input_path))
    if im is None:
        raise RuntimeError(f"failed to read image: {input_path}")

    services = get_sam3_services()
    predictor = services.get_semantic_predictor()
    predictor.set_image(im)

    # predictor.features is set after set_image
    features = getattr(predictor, "features", None)
    if features is None:
        raise RuntimeError("predictor.features not available")

    src_shape = (im.shape[0], im.shape[1])

    cache = get_embedding_cache()
    item = CachedEmbedding.new(features=features, src_shape=src_shape, ttl_sec=ttl_sec)
    cache.put(item)

    out_rel_dir = f"jobs/{job.id}"
    out_dir = jm.results_dir / out_rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save a small receipt file for traceability.
    (out_dir / "embedding.json").write_text(
        json.dumps({"embedding_id": item.embedding_id, "expires_at": item.expires_at}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    job.result = JobResult(
        files={"embedding": _files_url(f"{out_rel_dir}/embedding.json")},
        meta={"embedding_id": item.embedding_id, "expires_at": item.expires_at},
    )
    jm.persist(job)


def handle_embedding_query(job: Job, jm) -> None:
    embedding_id = str(job.payload["embedding_id"])
    query = job.payload["query"]

    cache = get_embedding_cache()
    cached = cache.get(embedding_id)
    if cached is None:
        job.status = "failed"
        job.error = JobError(message="embedding_id not found or expired")
        jm.persist(job)
        return

    services = get_sam3_services()
    predictor = services.get_semantic_predictor_for_features()

    out_rel_dir = f"jobs/{job.id}"
    out_dir = jm.results_dir / out_rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    masks_saved: list[str] = []

    if query.get("type") == "text":
        prompt = str(query.get("prompt", "")).strip()
        if not prompt:
            raise RuntimeError("empty prompt")
        masks, boxes = predictor.inference_features(cached.features, src_shape=cached.src_shape, text=[prompt])
    elif query.get("type") == "bboxes":
        bboxes = query.get("bboxes")
        masks, boxes = predictor.inference_features(cached.features, src_shape=cached.src_shape, bboxes=bboxes)
    else:
        raise RuntimeError("unsupported query.type")

    if masks is not None:
        masks_np = masks.detach().cpu().numpy()
        masks_dir = out_dir / "masks"
        for i, m in enumerate(masks_np):
            p = masks_dir / f"mask_{i:03d}.png"
            _save_mask_png(m, p)
            masks_saved.append(_files_url(f"{out_rel_dir}/masks/{p.name}"))

    job.result = JobResult(files={"masks": masks_saved}, meta={"embedding_id": embedding_id, "num_masks": len(masks_saved)})
    jm.persist(job)


def _video_props(video_path: Path) -> tuple[float, int, int, int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"failed to open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    return fps, w, h, n


def handle_video_bbox(job: Job, jm) -> None:
    video_path = Path(job.payload["video_path"])
    bboxes = job.payload["bboxes"]

    fps, w, h, total = _video_props(video_path)

    services = get_sam3_services()
    predictor = services.get_video_predictor()

    out_rel_dir = f"jobs/{job.id}"
    out_dir = jm.results_dir / out_rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    out_video = out_dir / "output.mp4"
    writer = cv2.VideoWriter(str(out_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    i = 0
    for r in predictor(source=str(video_path), bboxes=bboxes, stream=True):
        frame = r.plot() if hasattr(r, "plot") else getattr(r, "orig_img", None)
        if frame is None:
            continue
        writer.write(frame)
        i += 1
        if total > 0:
            job.progress = min(0.99, i / float(total))
            jm.persist(job)

    writer.release()

    job.result = JobResult(files={"video": _files_url(f"{out_rel_dir}/output.mp4")}, meta={"frames": i})
    jm.persist(job)


def handle_video_text(job: Job, jm) -> None:
    video_path = Path(job.payload["video_path"])
    prompt = str(job.payload["prompt"]).strip()

    fps, w, h, total = _video_props(video_path)

    services = get_sam3_services()
    predictor = services.get_video_semantic_predictor()

    out_rel_dir = f"jobs/{job.id}"
    out_dir = jm.results_dir / out_rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    out_video = out_dir / "output.mp4"
    writer = cv2.VideoWriter(str(out_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    i = 0
    for r in predictor(source=str(video_path), text=[prompt], stream=True):
        frame = r.plot() if hasattr(r, "plot") else getattr(r, "orig_img", None)
        if frame is None:
            continue
        writer.write(frame)
        i += 1
        if total > 0:
            job.progress = min(0.99, i / float(total))
            jm.persist(job)

    writer.release()

    job.result = JobResult(files={"video": _files_url(f"{out_rel_dir}/output.mp4")}, meta={"frames": i, "prompt": prompt})
    jm.persist(job)
