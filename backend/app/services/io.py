from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import UploadFile


def save_upload_file(upload: UploadFile, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
