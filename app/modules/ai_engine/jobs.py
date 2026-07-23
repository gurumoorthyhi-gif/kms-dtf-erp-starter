"""Background AI job lifecycle, progress, cancellation, and retry."""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from app.modules.ai_engine.client import (
    AIEngineClient,
    AIEngineError,
    AIEngineUnavailableError,
)
from app.modules.ai_engine.results import AIResultHandler
from app.modules.ai_engine.schemas import AIJobRequest, AIJobSnapshot, AIJobStatus

JobListener = Callable[[AIJobSnapshot], None]


@dataclass(slots=True)
class _ManagedJob:
    id: str
    request: AIJobRequest
    listener: JobListener | None
    engine_job_id: str = ""
    status: AIJobStatus = AIJobStatus.QUEUED
    progress: int = 0
    message: str = "Queued"
    attempts: int = 0
    result_preview_path: Path | None = None
    cancellation: threading.Event = field(default_factory=threading.Event)


class AIJobManager:
    def __init__(
        self,
        client: AIEngineClient,
        result_handler: AIResultHandler,
        results_directory: Path,
        *,
        poll_interval: float = 1,
        retry_delay: float = 1,
        max_attempts: int = 3,
    ) -> None:
        self.client = client
        self.result_handler = result_handler
        self.results_directory = results_directory.resolve()
        self.results_directory.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval
        self.retry_delay = retry_delay
        self.max_attempts = max_attempts
        self._jobs: dict[str, _ManagedJob] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="kms-ai")

    def submit(self, request: AIJobRequest, listener: JobListener | None = None) -> str:
        local_id = uuid4().hex
        job = _ManagedJob(local_id, request, listener)
        with self._lock:
            self._jobs[local_id] = job
        self._notify(job)
        self._executor.submit(self._run, job)
        return local_id

    def snapshot(self, job_id: str) -> AIJobSnapshot:
        with self._lock:
            job = self._jobs[job_id]
            return self._snapshot(job)

    def cancel(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job.status in {AIJobStatus.COMPLETED, AIJobStatus.CANCELLED}:
                return
            job.cancellation.set()
            job.status = AIJobStatus.CANCELLED
            job.message = "Cancellation requested"
            engine_job_id = job.engine_job_id
            self._notify(job)
        if engine_job_id:
            self._executor.submit(self._cancel_remote, engine_job_id)

    def retry(self, job_id: str, listener: JobListener | None = None) -> str:
        snapshot = self.snapshot(job_id)
        if snapshot.status not in {AIJobStatus.FAILED, AIJobStatus.CANCELLED}:
            raise ValueError("Only failed or cancelled jobs can be retried")
        return self.submit(snapshot.request, listener)

    def close(self) -> None:
        with self._lock:
            for job in self._jobs.values():
                if job.status in {AIJobStatus.QUEUED, AIJobStatus.RUNNING}:
                    job.cancellation.set()
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _run(self, job: _ManagedJob) -> None:
        try:
            response = self._submit_with_retry(job)
            if response is None:
                return
            if job.cancellation.is_set():
                self._cancel_remote(response.job_id)
                return
            with self._lock:
                job.engine_job_id = response.job_id
                job.status = (
                    AIJobStatus.RUNNING
                    if response.status == AIJobStatus.COMPLETED
                    else response.status
                )
                job.progress = (
                    min(response.progress, 99)
                    if response.status == AIJobStatus.COMPLETED
                    else response.progress
                )
                job.message = (
                    "Receiving result"
                    if response.status == AIJobStatus.COMPLETED
                    else response.message or "Submitted"
                )
                self._notify(job)
            if response.status == AIJobStatus.COMPLETED:
                self._complete(job)
                return
            if response.status in {AIJobStatus.FAILED, AIJobStatus.CANCELLED}:
                return
            while not job.cancellation.wait(self.poll_interval):
                response = self.client.status(job.engine_job_id)
                with self._lock:
                    job.status = (
                        AIJobStatus.RUNNING
                        if response.status == AIJobStatus.COMPLETED
                        else response.status
                    )
                    job.progress = (
                        min(response.progress, 99)
                        if response.status == AIJobStatus.COMPLETED
                        else response.progress
                    )
                    job.message = (
                        "Receiving result"
                        if response.status == AIJobStatus.COMPLETED
                        else response.message
                    )
                    self._notify(job)
                if response.status == AIJobStatus.COMPLETED:
                    self._complete(job)
                    return
                if response.status in {AIJobStatus.FAILED, AIJobStatus.CANCELLED}:
                    return
        except (AIEngineError, OSError, ValueError) as error:
            self._fail(job, str(error))

    def _submit_with_retry(self, job: _ManagedJob):
        while job.attempts < self.max_attempts and not job.cancellation.is_set():
            job.attempts += 1
            try:
                return self.client.submit(job.request)
            except AIEngineUnavailableError:
                if job.attempts >= self.max_attempts:
                    raise
                with self._lock:
                    job.message = (
                        f"Service unavailable; retrying ({job.attempts}/{self.max_attempts})"
                    )
                    self._notify(job)
                if job.cancellation.wait(self.retry_delay):
                    return None
        return None

    def _complete(self, job: _ManagedJob) -> None:
        result = self.results_directory / f"{job.id}.png"
        self.client.download_result(job.engine_job_id, result)
        preview = self.result_handler.save(job.request.artwork_id, result, job.request.tool.value)
        with self._lock:
            job.result_preview_path = preview
            job.status = AIJobStatus.COMPLETED
            job.progress = 100
            job.message = "Result saved as a new artwork version"
            self._notify(job)

    def _fail(self, job: _ManagedJob, message: str) -> None:
        with self._lock:
            if job.status != AIJobStatus.CANCELLED:
                job.status = AIJobStatus.FAILED
                job.message = message
                self._notify(job)

    def _cancel_remote(self, engine_job_id: str) -> None:
        try:
            self.client.cancel(engine_job_id)
        except AIEngineError:
            pass

    def _notify(self, job: _ManagedJob) -> None:
        if job.listener is not None:
            job.listener(self._snapshot(job))

    @staticmethod
    def _snapshot(job: _ManagedJob) -> AIJobSnapshot:
        return AIJobSnapshot(
            job.id,
            job.engine_job_id,
            job.request,
            job.status,
            job.progress,
            job.message,
            job.attempts,
            job.result_preview_path,
        )
