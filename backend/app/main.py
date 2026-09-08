from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import Settings
from app.game.state import GameError, InMemoryGameStore
from app.quantum.backend import AerStatevectorBackend, QuantumBackend
from app.quantum.hardware import IBMHardwareRunner
from app.quantum.jobs import InMemoryHardwareJobStore


def create_app(
    store: InMemoryGameStore | None = None,
    quantum_backend: QuantumBackend | None = None,
    settings: Settings | None = None,
    hardware: IBMHardwareRunner | None = None,
    hardware_jobs: InMemoryHardwareJobStore | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()

    app = FastAPI(title="Quantum Wordle API", version="0.3.0")
    app.state.settings = settings
    app.state.store = store or InMemoryGameStore()
    app.state.quantum_backend = quantum_backend or AerStatevectorBackend()
    app.state.hardware = hardware or IBMHardwareRunner(settings.hardware)
    app.state.hardware_jobs = hardware_jobs or InMemoryHardwareJobStore(
        max_per_hour=settings.hardware.max_jobs_per_hour,
        max_per_day=settings.hardware.max_jobs_per_day,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(GameError)
    async def game_error_handler(_: Request, exc: GameError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Map pydantic request-validation failures onto the same envelope
        # the rest of the API uses, instead of FastAPI's default {"detail": ...}.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "request validation failed",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, object]:
        return {"status": "ok", "hardware": app.state.hardware.available}

    app.include_router(router, prefix="/api/v1")

    # Single-container deployment: the built frontend is served from the same
    # origin as the API, so there is no CORS hop in production. Mounted last so
    # that /api/v1 and /healthz keep priority over the catch-all.
    if settings.static_dir is not None:
        _mount_frontend(app, settings.static_dir)

    return app


def _mount_frontend(app: FastAPI, directory: Path) -> None:
    app.mount("/", StaticFiles(directory=directory, html=True), name="frontend")


app = create_app()
