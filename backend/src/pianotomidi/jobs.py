"""In-memory job queue with one worker; a job expires an hour after its last request."""

import asyncio
import contextlib
import shutil
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from pianotomidi.audio import AudioError, decode
from pianotomidi.transcription import Transcriber, Transcription


class Status(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    filename: str
    audio_path: Path
    status: Status = Status.QUEUED
    progress: float = 0.0  # 0-1 while running
    error: str | None = None  # why it failed, e.g. "too_long", "not_audio"
    seconds: float | None = None  # length of the recording, once decoded
    result: Transcription | None = None
    created_at: float = field(default_factory=time.monotonic)
    touched_at: float = field(default_factory=time.monotonic)


class QueueFullError(Exception):
    pass


class JobStore:
    def __init__(
        self,
        transcriber: Transcriber,
        max_seconds: float,
        ttl_seconds: float = 3600,
        max_waiting: int = 20,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._transcriber = transcriber
        self._max_seconds = max_seconds
        self._ttl = ttl_seconds
        self._max_waiting = max_waiting
        self._clock = clock
        self._jobs: dict[str, Job] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._waiting: list[str] = []
        self._folder = Path(tempfile.mkdtemp(prefix="pianotomidi-"))
        self._worker: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._worker = asyncio.create_task(self._work())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker
        shutil.rmtree(self._folder, ignore_errors=True)

    def new_upload_path(self, suffix: str) -> Path:
        safe = "".join(c for c in suffix.lower() if c.isalnum())[:8]
        return self._folder / f"{uuid.uuid4().hex}.{safe or 'audio'}"

    def submit(self, audio_path: Path, filename: str) -> Job:
        if len(self._waiting) >= self._max_waiting:
            audio_path.unlink(missing_ok=True)
            raise QueueFullError
        now = self._clock()
        job = Job(
            id=uuid.uuid4().hex, filename=filename, audio_path=audio_path, created_at=now, touched_at=now
        )
        self._jobs[job.id] = job
        self._waiting.append(job.id)
        self._queue.put_nowait(job.id)
        return job

    def get(self, job_id: str) -> Job | None:
        self.sweep()
        job = self._jobs.get(job_id)
        if job:
            job.touched_at = self._clock()
        return job

    def position(self, job: Job) -> int | None:
        """How many jobs wait ahead of this one (0: next), or None when it isn't waiting."""
        return self._waiting.index(job.id) if job.id in self._waiting else None

    def delete(self, job_id: str) -> bool:
        job = self._jobs.pop(job_id, None)
        if job is None:
            return False
        if job.id in self._waiting:
            self._waiting.remove(job.id)
        job.audio_path.unlink(missing_ok=True)
        return True

    def sweep(self) -> None:
        """Forget jobs nobody has asked about for the TTL (a running job is never dropped)."""
        cutoff = self._clock() - self._ttl
        for job in list(self._jobs.values()):
            if job.touched_at < cutoff and job.status is not Status.RUNNING:
                self.delete(job.id)

    async def _work(self) -> None:
        while True:
            job_id = await self._queue.get()
            job = self._jobs.get(job_id)
            if job is None or job_id not in self._waiting:
                continue  # deleted while waiting
            self._waiting.remove(job_id)
            job.status = Status.RUNNING
            try:
                await asyncio.to_thread(self._run, job)
                job.status = Status.DONE
            except AudioError as e:
                job.status, job.error = Status.FAILED, e.reason
            except Exception:
                job.status, job.error = Status.FAILED, "internal"
            job.touched_at = self._clock()
            self.sweep()

    def _run(self, job: Job) -> None:
        audio = decode(job.audio_path, rate=self._transcriber.sample_rate, max_seconds=self._max_seconds)
        job.seconds = audio.seconds

        def report(fraction: float) -> None:
            job.progress = fraction

        job.result = self._transcriber.transcribe(audio, report)
        job.progress = 1.0
