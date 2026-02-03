from __future__ import annotations

import importlib

from fastapi import APIRouter

from ..core.config import get_settings

router = APIRouter()


@router.get("/health")
def health_v1():
    settings = get_settings()
    ul = None
    try:
        ul = importlib.import_module("ultralytics")
    except Exception:
        ul = None

    return {
        "ok": True,
        "ultralytics_installed": ul is not None,
        "ultralytics_version": getattr(ul, "__version__", None) if ul else None,
        "results_dir": settings.results_dir,
        "sam3_checkpoint_path": settings.sam3_checkpoint_path,
        "sam3_vocab_path": settings.sam3_vocab_path,
    }
