"""Async job queue for long-running simulations and research tasks."""

from __future__ import annotations

import asyncio
import time
import traceback
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.ids import new_id
from aimathh.core.logging import get_logger

log = get_logger("jobs")


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    id: str = ""
    name: str = ""
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: str = ""
    created_at: float = 0.0
    started_at: float = 0.0
    finished_at: float = 0.0
    checkpoints: list[dict[str, Any]] = Field(default_factory=list)

    def checkpoint(self, label: str, payload: dict[str, Any] | None = None) -> None:
        self.checkpoints.append({"label": label, "at": time.time(), **(payload or {})})


class JobQueue:
    """In-process asyncio job queue.

    A production deployment swaps this for Redis/RQ/Celery behind the same
    interface; all state transitions and checkpoints are explicit so jobs are
    resumable.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self.jobs: dict[str, Job] = {}
        self._sem = asyncio.Semaphore(max_workers)
        self._tasks: dict[str, asyncio.Task] = {}

    def submit(self, name: str, coro_fn: Callable[[Job], Awaitable[Any]]) -> Job:
        job = Job(id=new_id("job_"), name=name, created_at=time.time())
        self.jobs[job.id] = job
        task = asyncio.create_task(self._run(job, coro_fn))
        self._tasks[job.id] = task
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def list(self) -> list[Job]:
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)

    def cancel(self, job_id: str) -> bool:
        task = self._tasks.get(job_id)
        job = self.jobs.get(job_id)
        if task is None or job is None:
            return False
        if job.status in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED):
            return False
        task.cancel()
        job.status = JobStatus.CANCELLED
        job.finished_at = time.time()
        return True

    async def _run(self, job: Job, coro_fn: Callable[[Job], Awaitable[Any]]) -> None:
        async with self._sem:
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
            job.message = "running"
            try:
                job.result = await coro_fn(job)
                job.status = JobStatus.DONE
                job.progress = 1.0
                job.message = "done"
            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                job.message = "cancelled"
            except Exception as e:  # noqa: BLE001
                job.status = JobStatus.FAILED
                job.error = f"{e}\n{traceback.format_exc(limit=5)}"
                job.message = str(e)
                log.error("job %s failed: %s", job.id, e)
            finally:
                job.finished_at = time.time()


_queue: JobQueue | None = None


def get_job_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue
