from __future__ import annotations

import logging
import queue
import threading
import uuid
from pathlib import Path
from typing import Any, Callable

from ..core.config import get_settings
from .models import Job, JobError, JobResult, now_iso
from .store import JobStore


JobHandler = Callable[[Job, "JobManager"], None]


logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self, results_dir: Path):
        self._results_dir = results_dir
        self._jobs_dir = results_dir / "jobs"
        self._store = JobStore(results_dir / "status.json")
        self._queue: "queue.Queue[Job]" = queue.Queue()
        self._handlers: dict[str, JobHandler] = {}
        self._worker_thread: threading.Thread | None = None
        self._stop = threading.Event()

        self._mark_incomplete_jobs_failed()

    @property
    def results_dir(self) -> Path:
        return self._results_dir

    def job_dir(self, job_id: str) -> Path:
        return self._jobs_dir / job_id

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    def persist(self, job: Job) -> None:
        self._store.upsert(job)

    def create(self, job_type: str, payload: dict[str, Any]) -> Job:
        job_id = uuid.uuid4().hex
        return self.create_with_id(job_id=job_id, job_type=job_type, payload=payload)

    def create_with_id(self, job_id: str, job_type: str, payload: dict[str, Any]) -> Job:
        job = Job(id=job_id, type=job_type, status="queued", created_at=now_iso(), payload=payload)
        self._store.upsert(job)
        self._queue.put(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._store.get(job_id)

    def start(self) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._stop.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, name="job-worker", daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _mark_incomplete_jobs_failed(self) -> None:
        # On restart, mark queued/running jobs as failed to avoid hanging states.
        for job_id in self._store.list_ids():
            job = self._store.get(job_id)
            if not job:
                continue
            if job.status in {"queued", "running"}:
                job.status = "failed"
                job.finished_at = now_iso()
                job.error = JobError(message="server_restart")
                self._store.upsert(job)

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue

            handler = self._handlers.get(job.type)
            if not handler:
                job.status = "failed"
                job.started_at = job.started_at or now_iso()
                job.finished_at = now_iso()
                job.error = JobError(message=f"No handler registered for job type: {job.type}")
                self._store.upsert(job)
                continue

            job.status = "running"
            job.started_at = now_iso()
            job.progress = 0.0
            self._store.upsert(job)

            try:
                handler(job, self)
                if job.status == "running":
                    job.status = "succeeded"
                job.progress = 1.0
                job.finished_at = now_iso()
                self._store.upsert(job)
            except Exception as e:
                logger.exception("Job failed: id=%s type=%s", job.id, job.type)
                job.status = "failed"
                job.finished_at = now_iso()
                msg = str(e)
                if not msg:
                    msg = repr(e)
                job.error = JobError(message=f"{type(e).__name__}: {msg}")
                self._store.upsert(job)


_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    global _manager
    if _manager is None:
        settings = get_settings()
        results_dir = Path(settings.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        _manager = JobManager(results_dir=results_dir)
    return _manager
