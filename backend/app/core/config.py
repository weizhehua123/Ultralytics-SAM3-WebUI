from __future__ import annotations

import os
import platform
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_results_dir() -> str:
    # Prefer absolute path on Linux servers; fallback to ./output (ignored by sftp.json) for local dev.
    if platform.system().lower() == "linux":
        return "/mnt/cloud-disk/sam3-webui/results"
    return str(Path("output").resolve())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    host: str = Field(default=os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default=int(os.getenv("PORT", "8002")))

    api_prefix: str = "/api/v1"

    sam3_checkpoint_path: str = Field(
        default=os.getenv("SAM3_CHECKPOINT_PATH", "/mnt/cloud-disk/models/sam3/facebook/sam3/sam3.pt")
    )
    sam3_vocab_path: str = Field(
        default=os.getenv(
            "SAM3_VOCAB_PATH",
            "/mnt/cloud-disk/models/sam3/facebook/sam3/bpe_simple_vocab_16e6.txt.gz",
        )
    )

    device: str = Field(default=os.getenv("SAM3_DEVICE", ""))
    half: bool = Field(default=os.getenv("SAM3_HALF", "1") not in {"0", "false", "False"})
    conf: float = Field(default=float(os.getenv("SAM3_CONF", "0.25")))
    imgsz: int | None = Field(default=int(os.getenv("SAM3_IMGSZ", "0")) or None)

    results_dir: str = Field(default=os.getenv("RESULTS_DIR", _default_results_dir()))

    embedding_cache_size: int = Field(default=int(os.getenv("EMBEDDING_CACHE_SIZE", "8")))


def get_settings() -> Settings:
    return Settings()


def ensure_dirs(settings: Settings) -> None:
    Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
