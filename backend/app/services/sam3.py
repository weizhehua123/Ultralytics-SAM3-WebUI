from __future__ import annotations

from typing import Any

from ..core.config import get_settings


class SAM3Services:
    """Lazy-loaded SAM3 predictors.

    Implemented in next step: we defer imports so local dev without ultralytics still runs /health.
    """

    def __init__(self) -> None:
        self._semantic_predictor = None
        self._semantic_predictor_for_features = None
        self._video_predictor = None
        self._video_semantic_predictor = None

    def get_semantic_predictor(self):
        if self._semantic_predictor is None:
            settings = get_settings()
            from ultralytics.models.sam import SAM3SemanticPredictor

            overrides: dict[str, Any] = dict(
                conf=settings.conf,
                task="segment",
                mode="predict",
                model=settings.sam3_checkpoint_path,
                half=settings.half,
                verbose=False,
            )
            if settings.imgsz is not None:
                overrides["imgsz"] = settings.imgsz
            self._semantic_predictor = SAM3SemanticPredictor(overrides=overrides)
        return self._semantic_predictor

    def get_semantic_predictor_for_features(self):
        if self._semantic_predictor_for_features is None:
            settings = get_settings()
            from ultralytics.models.sam import SAM3SemanticPredictor

            overrides: dict[str, Any] = dict(
                conf=settings.conf,
                task="segment",
                mode="predict",
                model=settings.sam3_checkpoint_path,
                half=settings.half,
                verbose=False,
            )
            if settings.imgsz is not None:
                overrides["imgsz"] = settings.imgsz
            self._semantic_predictor_for_features = SAM3SemanticPredictor(overrides=overrides)
            # Ensure model is ready for inference_features.
            self._semantic_predictor_for_features.setup_model()
        return self._semantic_predictor_for_features

    def get_video_predictor(self):
        if self._video_predictor is None:
            settings = get_settings()
            from ultralytics.models.sam import SAM3VideoPredictor

            overrides: dict[str, Any] = dict(
                conf=settings.conf,
                task="segment",
                mode="predict",
                model=settings.sam3_checkpoint_path,
                half=settings.half,
                verbose=False,
            )
            if settings.imgsz is not None:
                overrides["imgsz"] = settings.imgsz
            self._video_predictor = SAM3VideoPredictor(overrides=overrides)
        return self._video_predictor

    def get_video_semantic_predictor(self):
        if self._video_semantic_predictor is None:
            settings = get_settings()
            from ultralytics.models.sam import SAM3VideoSemanticPredictor

            overrides: dict[str, Any] = dict(
                conf=settings.conf,
                task="segment",
                mode="predict",
                model=settings.sam3_checkpoint_path,
                half=settings.half,
                verbose=False,
            )
            if settings.imgsz is not None:
                overrides["imgsz"] = settings.imgsz
            self._video_semantic_predictor = SAM3VideoSemanticPredictor(overrides=overrides)
        return self._video_semantic_predictor


_services: SAM3Services | None = None


def get_sam3_services() -> SAM3Services:
    global _services
    if _services is None:
        _services = SAM3Services()
    return _services
