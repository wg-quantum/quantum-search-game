from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.game.state import GameError, InMemoryGameStore
from app.quantum.backend import AerStatevectorBackend, QuantumBackend


def create_app(
    store: InMemoryGameStore | None = None,
    quantum_backend: QuantumBackend | None = None,
) -> FastAPI:
    app = FastAPI(title="Quantum Wordle API", version="0.2.0")
    app.state.store = store or InMemoryGameStore()
    app.state.quantum_backend = quantum_backend or AerStatevectorBackend()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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

    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
