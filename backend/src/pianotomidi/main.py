"""uv run uvicorn pianotomidi.main:app --port 8100"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pianotomidi.api import router as jobs_router
from pianotomidi.config import get_settings
from pianotomidi.jobs import JobStore
from pianotomidi.transcription import TranskunTranscriber


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        model = await asyncio.to_thread(TranskunTranscriber)
        jobs = JobStore(
            model, max_seconds=settings.max_audio_minutes * 60, ttl_seconds=settings.job_ttl_minutes * 60
        )
        jobs.start()
        app.state.jobs = jobs
        app.state.max_upload_bytes = settings.max_upload_mb * 1024 * 1024
        yield
        await jobs.stop()

    app = FastAPI(title="Piano to MIDI API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Disposition"],
    )
    app.include_router(jobs_router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/limits", tags=["meta"])
    def limits() -> dict[str, float]:
        """What an upload may be, so the web app can check before sending."""
        return {"max_upload_mb": settings.max_upload_mb, "max_audio_minutes": settings.max_audio_minutes}

    return app


app = create_app()
