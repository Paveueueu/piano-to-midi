"""HTTP endpoints for transcription jobs."""

from pathlib import Path, PurePath
from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel

from pianotomidi.jobs import Job, JobStore, QueueFullError, Status
from pianotomidi.midi import to_midi
from pianotomidi.options import Options, arrange

router = APIRouter(prefix="/jobs", tags=["jobs"])

CHUNK = 1024 * 1024


class JobOut(BaseModel):
    id: str
    filename: str
    status: Status
    progress: float
    position: int | None  # jobs waiting ahead of this one; None when not waiting
    error: str | None
    seconds: float | None
    notes: int | None
    pedals: int | None


class NoteOut(BaseModel):
    start: float
    end: float
    pitch: int
    velocity: int


class PedalOut(BaseModel):
    start: float
    end: float
    kind: Literal["sustain", "soft"]
    value: int


class NotesOut(BaseModel):
    seconds: float
    notes: list[NoteOut]
    pedals: list[PedalOut]


def _store(request: Request) -> JobStore:
    store: JobStore = request.app.state.jobs
    return store


def _out(store: JobStore, job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        filename=job.filename,
        status=job.status,
        progress=round(job.progress, 3),
        position=store.position(job),
        error=job.error,
        seconds=job.seconds,
        notes=len(job.result.notes) if job.result else None,
        pedals=len(job.result.pedals) if job.result else None,
    )


def _job(store: JobStore, job_id: str) -> Job:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such job (it may have expired)")
    return job


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=JobOut)
async def create_job(request: Request, file: Annotated[UploadFile, File()]) -> JobOut:
    """Upload a recording; transcription starts as soon as the jobs ahead are done."""
    store = _store(request)
    max_bytes = request.app.state.max_upload_bytes
    filename = PurePath(file.filename or "recording").name
    path = store.new_upload_path(PurePath(filename).suffix)
    size = 0
    with Path(path).open("wb") as out:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                path.unlink(missing_ok=True)
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "too_large")
            out.write(chunk)
    if size == 0:
        path.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty")
    try:
        job = store.submit(path, filename)
    except QueueFullError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "busy") from e
    return _out(store, job)


@router.get("/{job_id}", response_model=JobOut)
def get_job(request: Request, job_id: str) -> JobOut:
    store = _store(request)
    return _out(store, _job(store, job_id))


@router.get("/{job_id}/notes", response_model=NotesOut)
def get_notes(request: Request, job_id: str) -> NotesOut:
    """The transcription as data, for drawing a piano roll."""
    job = _job(_store(request), job_id)
    if job.status is not Status.DONE or job.result is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "not_ready")
    r = job.result
    return NotesOut(
        seconds=r.seconds,
        notes=[NoteOut(start=n.start, end=n.end, pitch=n.pitch, velocity=n.velocity) for n in r.notes],
        pedals=[PedalOut(start=p.start, end=p.end, kind=p.kind, value=p.value) for p in r.pedals],
    )


@router.get("/{job_id}/midi", response_class=Response, responses={200: {"content": {"audio/midi": {}}}})
def get_midi(request: Request, job_id: str) -> Response:
    job = _job(_store(request), job_id)
    if job.status is not Status.DONE or job.result is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "not_ready")
    name = PurePath(job.filename).stem or "transcription"
    safe = "".join(c if c.isalnum() or c in "-_ ()[]" else "_" for c in name)[:80]
    return Response(
        content=to_midi(arrange(job.result, Options()), name=safe),
        media_type="audio/midi",
        headers={"Content-Disposition": f'attachment; filename="{safe}.mid"'},
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(request: Request, job_id: str) -> Response:
    if not _store(request).delete(job_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such job")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
