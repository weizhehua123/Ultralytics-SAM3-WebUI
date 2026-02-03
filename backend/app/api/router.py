from __future__ import annotations

from fastapi import APIRouter

from .routes_health import router as health_router
from .routes_image import router as image_router
from .routes_jobs import router as jobs_router
from .routes_video import router as video_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(image_router, prefix="/image", tags=["image"])
api_router.include_router(video_router, prefix="/video", tags=["video"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
