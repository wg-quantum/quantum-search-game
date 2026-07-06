from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.game.dictionary import load_words
from app.game.state import MAX_TURNS, WORD_LENGTH, GameError, GameState, GameStore
from app.quantum.circuit import MAX_DRAWN as CIRCUIT_MAX_DRAWN
from app.quantum.circuit import circuit_svg
from app.quantum.engine import (
    MAX_ITERATIONS,
    MAX_SHOTS,
    N_QUBITS,
    measure,
    run_grover,
)

router = APIRouter()


# ---- schemas ----

class CreateGameResponse(BaseModel):
    game_id: str
    max_turns: int
    word_length: int
    dictionary_size: int


class GuessEntry(BaseModel):
    word: str
    feedback: list[str]


class GameStateResponse(BaseModel):
    status: str
    turn: int
    max_turns: int
    guesses: list[GuessEntry]
    candidate_count: int


class GuessRequest(BaseModel):
    word: str = Field(min_length=WORD_LENGTH, max_length=WORD_LENGTH)


class GuessResponse(BaseModel):
    feedback: list[str]
    status: str
    turn: int
    candidate_count: int


class CandidatesResponse(BaseModel):
    total: int
    words: list[str]


# ---- helpers ----

def _store(request: Request) -> GameStore:
    return request.app.state.store


def _state_response(game: GameState) -> GameStateResponse:
    return GameStateResponse(
        status=game.status,
        turn=game.turn,
        max_turns=MAX_TURNS,
        guesses=[
            GuessEntry(word=w, feedback=[t.value for t in fb])
            for w, fb in game.history
        ],
        candidate_count=len(game.candidate_indices()),
    )


# ---- endpoints ----

@router.post("/games", response_model=CreateGameResponse, status_code=201)
def create_game(request: Request) -> CreateGameResponse:
    game = _store(request).create()
    return CreateGameResponse(
        game_id=game.game_id,
        max_turns=MAX_TURNS,
        word_length=WORD_LENGTH,
        dictionary_size=len(load_words()),
    )


@router.get("/games/{game_id}", response_model=GameStateResponse)
def get_game(game_id: str, request: Request) -> GameStateResponse:
    return _state_response(_store(request).get(game_id))


@router.post("/games/{game_id}/guesses", response_model=GuessResponse)
def post_guess(game_id: str, body: GuessRequest, request: Request) -> GuessResponse:
    game = _store(request).get(game_id)
    fb = game.apply_guess(body.word)
    return GuessResponse(
        feedback=[t.value for t in fb],
        status=game.status,
        turn=game.turn,
        candidate_count=len(game.candidate_indices()),
    )


@router.get("/games/{game_id}/candidates", response_model=CandidatesResponse)
def get_candidates(
    game_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CandidatesResponse:
    game = _store(request).get(game_id)
    indices = game.candidate_indices()
    words = load_words()
    return CandidatesResponse(
        total=len(indices),
        words=[words[i] for i in indices[offset : offset + limit]],
    )


# ---- quantum (Phase 3) ----

class QuantumRunRequest(BaseModel):
    iterations: int = Field(ge=0, le=MAX_ITERATIONS)


class StateProb(BaseModel):
    index: int
    word: str | None  # None = padding state outside the dictionary
    probability: float
    is_candidate: bool


class SnapshotEntry(BaseModel):
    iteration: int
    top: list[StateProb]
    others_probability: float
    candidate_probability: float


class QuantumRunResponse(BaseModel):
    n_qubits: int
    n_states: int
    candidate_count: int
    optimal_iterations: int
    iterations: int
    snapshots: list[SnapshotEntry]


TOP_K = 20


@router.post("/games/{game_id}/quantum/run", response_model=QuantumRunResponse)
def quantum_run(
    game_id: str, body: QuantumRunRequest, request: Request
) -> QuantumRunResponse:
    game = _store(request).get(game_id)
    marked = game.candidate_indices()
    if not marked:
        raise GameError("no_candidates", "candidate set is empty")

    result = run_grover(
        request.app.state.quantum_backend, marked, body.iterations
    )
    words = load_words()
    marked_set = set(marked)

    snapshots: list[SnapshotEntry] = []
    for snap in result.snapshots:
        p = snap.probabilities
        top_idx = p.argsort()[::-1][:TOP_K]
        top = [
            StateProb(
                index=int(i),
                word=words[i] if i < len(words) else None,
                probability=float(p[i]),
                is_candidate=int(i) in marked_set,
            )
            for i in top_idx
        ]
        snapshots.append(
            SnapshotEntry(
                iteration=snap.iteration,
                top=top,
                others_probability=float(1.0 - p[top_idx].sum()),
                candidate_probability=snap.marked_probability(marked),
            )
        )

    return QuantumRunResponse(
        n_qubits=result.n_qubits,
        n_states=result.n_states,
        candidate_count=len(marked),
        optimal_iterations=result.optimal,
        iterations=body.iterations,
        snapshots=snapshots,
    )


class QuantumMeasureRequest(BaseModel):
    iterations: int = Field(ge=0, le=MAX_ITERATIONS)
    shots: int = Field(default=1, ge=1, le=MAX_SHOTS)


class MeasureResult(BaseModel):
    index: int
    word: str | None
    is_candidate: bool
    count: int


class QuantumMeasureResponse(BaseModel):
    iterations: int
    shots: int
    results: list[MeasureResult]


@router.post("/games/{game_id}/quantum/measure", response_model=QuantumMeasureResponse)
def quantum_measure(
    game_id: str, body: QuantumMeasureRequest, request: Request
) -> QuantumMeasureResponse:
    game = _store(request).get(game_id)
    marked = game.candidate_indices()
    if not marked:
        raise GameError("no_candidates", "candidate set is empty")

    counts = measure(
        request.app.state.quantum_backend, marked, body.iterations, body.shots
    )
    words = load_words()
    marked_set = set(marked)
    results = [
        MeasureResult(
            index=i,
            word=words[i] if i < len(words) else None,
            is_candidate=i in marked_set,
            count=c,
        )
        for i, c in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    return QuantumMeasureResponse(
        iterations=body.iterations, shots=body.shots, results=results
    )


class CircuitResponse(BaseModel):
    iterations: int
    drawn_iterations: int
    svg: str


@router.get("/games/{game_id}/quantum/circuit", response_model=CircuitResponse)
def quantum_circuit(
    game_id: str,
    request: Request,
    iterations: int = Query(ge=0, le=MAX_ITERATIONS),
) -> CircuitResponse:
    _store(request).get(game_id)  # validate game exists
    drawn = min(iterations, CIRCUIT_MAX_DRAWN)
    return CircuitResponse(
        iterations=iterations,
        drawn_iterations=drawn,
        svg=circuit_svg(drawn),
    )
