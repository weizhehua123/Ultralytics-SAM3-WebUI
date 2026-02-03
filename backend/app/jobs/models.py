from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

JobStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass
class JobError:
    message: str


@dataclass
class JobResult:
    files: dict[str, str] = field(default_factory=dict)  # name -> url path under /files
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Job:
    id: str
    type: str
    status: JobStatus
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    progress: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: JobResult | None = None
    error: JobError | None = None

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        return raw


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
