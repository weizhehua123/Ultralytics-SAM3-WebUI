from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .models import Job


class JobStore:
    def __init__(self, status_file: Path):
        self._status_file = status_file
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._last_mtime: float | None = None
        self._load()

    def _load(self) -> None:
        if not self._status_file.exists():
            return
        try:
            data = json.loads(self._status_file.read_text(encoding="utf-8"))
            jobs = data.get("jobs", {})
            for job_id, job_dict in jobs.items():
                self._jobs[job_id] = Job(**job_dict)
            try:
                self._last_mtime = self._status_file.stat().st_mtime
            except Exception:
                self._last_mtime = None
        except Exception:
            # Corrupt status file should not prevent startup.
            self._jobs = {}

    def _reload_if_changed(self) -> None:
        if not self._status_file.exists():
            return
        try:
            mtime = self._status_file.stat().st_mtime
        except Exception:
            return
        if self._last_mtime is None or mtime > self._last_mtime:
            # Full reload is simple and reliable for this small status file.
            try:
                data = json.loads(self._status_file.read_text(encoding="utf-8"))
                jobs = data.get("jobs", {})
                self._jobs = {job_id: Job(**job_dict) for job_id, job_dict in jobs.items()}
                self._last_mtime = mtime
            except Exception:
                # Ignore reload errors; keep last known in-memory state.
                return

    def _atomic_write(self, data: dict[str, Any]) -> None:
        self._status_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._status_file.with_suffix(self._status_file.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._status_file)
        try:
            self._last_mtime = self._status_file.stat().st_mtime
        except Exception:
            self._last_mtime = None

    def _persist(self) -> None:
        data = {"jobs": {job_id: job.to_dict() for job_id, job in self._jobs.items()}}
        self._atomic_write(data)

    def upsert(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job
            self._persist()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            self._reload_if_changed()
            return self._jobs.get(job_id)

    def list_ids(self) -> list[str]:
        with self._lock:
            self._reload_if_changed()
            return list(self._jobs.keys())
