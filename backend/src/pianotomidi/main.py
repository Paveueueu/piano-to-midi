"""uv run uvicorn pianotomidi.main:app --port 8100"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pianotomidi.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Piano to MIDI API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/limits", tags=["meta"])
    def limits() -> dict[str, float]:
        """What an upload may be, so the web app can check before sending."""
        return {"max_upload_mb": settings.max_upload_mb, "max_audio_minutes": settings.max_audio_minutes}

    return app


app = create_app()
