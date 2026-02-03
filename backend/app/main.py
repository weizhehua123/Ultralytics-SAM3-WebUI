from __future__ import annotations

import importlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.router import api_router
from .core.config import ensure_dirs, get_settings
from .core.logging import setup_logging
from .jobs.manager import get_job_manager
from .jobs.handlers import (
    handle_embedding_create,
    handle_embedding_query,
    handle_image_exemplar,
    handle_image_text,
    handle_video_bbox,
    handle_video_text,
)


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    ensure_dirs(settings)

    app = FastAPI(title="Ultralytics SAM3 WebUI", version="0.1.0")

    # Resolve frontend directory once.
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"

    @app.on_event("startup")
    def _startup() -> None:
        jm = get_job_manager()
        jm.register_handler("image_text", handle_image_text)
        jm.register_handler("image_exemplar", handle_image_exemplar)
        jm.register_handler("embedding_create", handle_embedding_create)
        jm.register_handler("embedding_query", handle_embedding_query)
        jm.register_handler("video_bbox", handle_video_bbox)
        jm.register_handler("video_text", handle_video_text)
        jm.start()
        app.state.job_manager = jm

    # API
    app.include_router(api_router, prefix=settings.api_prefix)

    # Serve results files (absolute dir on server).
    app.mount("/files", StaticFiles(directory=settings.results_dir), name="files")

    @app.get("/health")
    def health():
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

    # For convenience, ensure root returns index.html.
    @app.get("/")
    def index():
        return FileResponse(frontend_dir / "index.html")

    # Serve frontend (static HTML) last so it doesn't shadow /health or /api.
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = create_app()
