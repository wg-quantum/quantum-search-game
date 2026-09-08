"""Hardware mode, verified without touching a QPU.

The parts that can be checked exactly are checked exactly: the downscaling
arithmetic, and that the MCZ-built circuit implements the same unitary as the
DiagonalGate circuit the Aer engine uses. Everything past job submission is
exercised through a fake runner, so the suite needs no credentials.
"""

import random

import pytest
from fastapi.testclient import TestClient
from qiskit.quantum_info import Statevector

from app.config import HardwareSettings, Settings
from app.game.state import InMemoryGameStore
from app.main import create_app
from app.quantum.backend import AerStatevectorBackend
from app.quantum.hardware import (
    MAX_ITERATIONS,
    SHORTLIST_SIZE,
    DownscaledProblem,
    JobUpdate,
    Submission,
    _counts_from_result,
    build_hardware_circuit,
    downscale,
    ideal_distribution,
    phase_oracle,
)
from app.quantum.jobs import (
    HardwareJobRecord,
    InMemoryHardwareJobStore,
    JobNotFound,
    QuotaExceeded,
)

WORDS = tuple(f"w{i:04d}" for i in range(2315))


# ---- downscaling ----

@pytest.mark.parametrize(
    ("m", "n_qubits", "marked"),
    [
        (1, 2, (0,)),
        (2, 3, (0, 4)),
        (3, 4, (0, 5, 10)),
        (4, 4, (0, 4, 8, 12)),
    ],
)
def test_downscale_shapes(m: int, n_qubits: int, marked: tuple[int, ...]):
    problem = downscale(list(range(m)), WORDS)
    assert problem.n_qubits == n_qubits
    assert problem.n_states == 1 << n_qubits
    assert problem.marked == marked
    assert problem.words == tuple(WORDS[:m])
    # 1/4 padding puts the optimum at a single iteration for every shortlist size
    assert problem.iterations == 1


def test_downscale_truncates_to_shortlist():
    problem = downscale(list(range(500)), WORDS)
    assert len(problem.marked) == SHORTLIST_SIZE
    assert problem.dictionary_indices == tuple(range(SHORTLIST_SIZE))
    assert problem.iterations <= MAX_ITERATIONS


def test_downscale_keeps_dictionary_indices_and_words_aligned():
    problem = downscale([7, 19, 88], WORDS)
    assert problem.dictionary_indices == (7, 19, 88)
    assert problem.words == (WORDS[7], WORDS[19], WORDS[88])
    assert [problem.word_at(s) for s in problem.marked] == list(problem.words)
    unmarked = next(s for s in range(problem.n_states) if s not in problem.marked)
    assert problem.word_at(unmarked) is None


def test_downscale_rejects_empty_candidates():
    with pytest.raises(ValueError):
        downscale([], WORDS)


# ---- circuit equivalence with the Aer engine ----

@pytest.mark.parametrize("m", [1, 2, 3, 4])
def test_hardware_circuit_matches_diagonal_gate_engine(m: int):
    """MCZ oracle + X-MCZ-X diffuser == DiagonalGate oracle + reflection."""
    problem = downscale(list(range(m)), WORDS)
    circuit = build_hardware_circuit(problem, measure=False)
    from_mcz = Statevector(circuit).probabilities()

    from_diagonal = AerStatevectorBackend(seed=7).run_grover(
        problem.n_qubits, problem.marked, problem.iterations
    )[-1]

    assert from_mcz == pytest.approx(from_diagonal, abs=1e-9)


@pytest.mark.parametrize("m", [1, 2, 3, 4])
def test_ideal_success_probability_is_near_certain(m: int):
    """The whole point of downscaling: any spread the QPU shows is device noise."""
    problem = downscale(list(range(m)), WORDS)
    ideal = ideal_distribution(AerStatevectorBackend(seed=7), problem)
    assert sum(ideal) == pytest.approx(1.0)
    assert sum(ideal[i] for i in problem.marked) > 0.94


def test_hardware_circuit_is_shallow_enough_for_nisq():
    problem = downscale(list(range(4)), WORDS)
    circuit = build_hardware_circuit(problem)
    assert circuit.num_qubits <= 4
    assert circuit.depth() < 60


def test_phase_oracle_rejects_out_of_range_state():
    with pytest.raises(ValueError):
        phase_oracle(2, [4])


def test_build_rejects_too_many_iterations():
    problem = downscale([0], WORDS)
    with pytest.raises(ValueError):
        build_hardware_circuit(
            DownscaledProblem(
                n_qubits=problem.n_qubits,
                n_states=problem.n_states,
                marked=problem.marked,
                words=problem.words,
                dictionary_indices=problem.dictionary_indices,
                iterations=MAX_ITERATIONS + 1,
            )
        )


# ---- result decoding ----

class _FakeBitArray:
    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts

    def get_counts(self) -> dict[str, int]:
        return self._counts


class _FakeData:
    def __init__(self, **registers: _FakeBitArray) -> None:
        self.__dict__.update(registers)

    def values(self) -> list[_FakeBitArray]:
        return list(self.__dict__.values())


class _FakePubResult:
    def __init__(self, data: _FakeData) -> None:
        self.data = data


def test_counts_decoded_from_meas_register():
    pub = _FakePubResult(_FakeData(meas=_FakeBitArray({"0000": 3, "1100": 5})))
    assert _counts_from_result(pub) == {0: 3, 12: 5}


def test_counts_decoded_from_the_only_register_when_not_named_meas():
    pub = _FakePubResult(_FakeData(c=_FakeBitArray({"11": 7})))
    assert _counts_from_result(pub) == {3: 7}


# ---- job store: quota and TTL ----

def _record(job_id: str) -> HardwareJobRecord:
    problem = downscale([0, 1, 2, 3], WORDS)
    return HardwareJobRecord(
        job_id=job_id,
        game_id="g",
        backend_name="fake_qpu",
        problem=problem,
        shots=128,
        depth=20,
        two_qubit_gates=12,
        ideal=ideal_distribution(AerStatevectorBackend(seed=1), problem),
    )


def test_quota_blocks_after_hourly_cap():
    store = InMemoryHardwareJobStore(max_per_hour=2, max_per_day=10)
    store.reserve()
    store.reserve()
    with pytest.raises(QuotaExceeded) as exc:
        store.reserve()
    assert exc.value.retry_after > 0
    assert store.quota_snapshot() == (2, 2)


def test_quota_blocks_after_daily_cap():
    store = InMemoryHardwareJobStore(max_per_hour=5, max_per_day=3)
    for _ in range(3):
        store.reserve()
    with pytest.raises(QuotaExceeded):
        store.reserve()


def test_release_returns_a_reserved_slot():
    store = InMemoryHardwareJobStore(max_per_hour=1, max_per_day=1)
    ticket = store.reserve()
    store.release(ticket)
    assert store.quota_snapshot() == (0, 0)
    store.reserve()  # slot is free again


def test_unknown_job_raises():
    store = InMemoryHardwareJobStore(max_per_hour=1, max_per_day=1)
    with pytest.raises(JobNotFound):
        store.get("nope")


def test_apply_merges_update_without_clearing_known_fields():
    store = InMemoryHardwareJobStore(max_per_hour=5, max_per_day=5)
    store.add(_record("job-1"))
    store.apply("job-1", JobUpdate(status="RUNNING"))
    assert store.get("job-1").counts is None
    record = store.apply(
        "job-1", JobUpdate(status="DONE", counts={0: 10}, qpu_seconds=2.5)
    )
    assert record.finished
    assert record.counts == {0: 10}
    assert record.qpu_seconds == 2.5
    # a later poll carrying no counts must not erase them
    assert store.apply("job-1", JobUpdate(status="DONE")).counts == {0: 10}


# ---- API ----

class _FakeRunner:
    """Stands in for IBMHardwareRunner: same surface, no network."""

    def __init__(self, *, available: bool = True, fail: Exception | None = None) -> None:
        self.settings = HardwareSettings(
            token="t" if available else None, shots=128, enabled=available
        )
        self.available = available
        self._fail = fail
        self.submitted: list[DownscaledProblem] = []
        self.updates: list[JobUpdate] = []

    def submit(self, problem: DownscaledProblem, shots: int) -> Submission:
        if self._fail is not None:
            raise self._fail
        self.submitted.append(problem)
        return Submission(
            job_id=f"fake-{len(self.submitted)}",
            backend_name="fake_qpu",
            depth=23,
            two_qubit_gates=14,
        )

    def poll(self, job_id: str) -> JobUpdate:
        return self.updates.pop(0) if self.updates else JobUpdate(status="QUEUED")


def _client(runner: _FakeRunner, **store_kwargs: int) -> TestClient:
    app = create_app(
        store=InMemoryGameStore(rng=random.Random(42)),
        settings=Settings(hardware=runner.settings),
        hardware=runner,
        hardware_jobs=InMemoryHardwareJobStore(
            max_per_hour=store_kwargs.get("max_per_hour", 5),
            max_per_day=store_kwargs.get("max_per_day", 5),
        ),
    )
    return TestClient(app)


def _game(client: TestClient) -> str:
    return client.post("/api/v1/games").json()["game_id"]


def test_info_reports_unavailable_without_credentials():
    client = _client(_FakeRunner(available=False))
    body = client.get("/api/v1/quantum/hardware").json()
    assert body["available"] is False
    assert body["reason"]
    assert body["shortlist_size"] == SHORTLIST_SIZE


def test_submit_refused_without_credentials():
    client = _client(_FakeRunner(available=False))
    res = client.post(f"/api/v1/games/{_game(client)}/quantum/hardware")
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "hardware_unavailable"


def test_submit_then_poll_to_completion():
    runner = _FakeRunner()
    client = _client(runner)
    game_id = _game(client)

    res = client.post(f"/api/v1/games/{game_id}/quantum/hardware")
    assert res.status_code == 202
    submitted = res.json()
    assert submitted["status"] == "QUEUED"
    assert submitted["backend"] == "fake_qpu"
    assert len(submitted["shortlist"]) == SHORTLIST_SIZE
    assert submitted["ideal_marked_probability"] > 0.94
    assert submitted["hardware_marked_probability"] is None
    assert len(submitted["states"]) == submitted["n_states"]

    job_id = submitted["job_id"]
    runner.updates = [
        JobUpdate(status="RUNNING"),
        JobUpdate(status="DONE", counts={0: 30, 4: 30, 8: 20, 12: 15, 1: 5}, qpu_seconds=2.0),
    ]
    assert client.get(f"/api/v1/quantum/jobs/{job_id}").json()["status"] == "RUNNING"

    done = client.get(f"/api/v1/quantum/jobs/{job_id}").json()
    assert done["status"] == "DONE"
    assert done["hardware_marked_probability"] == pytest.approx(95 / 100)
    assert done["qpu_seconds"] == 2.0
    marked = [s for s in done["states"] if s["is_marked"]]
    assert len(marked) == SHORTLIST_SIZE
    assert all(s["word"] for s in marked)
    assert all(s["word"] is None for s in done["states"] if not s["is_marked"])
    # the noisy leak into an unmarked state is reported, not hidden
    assert next(s for s in done["states"] if s["index"] == 1)["count"] == 5

    # finished jobs are served locally: no further polling of the service
    runner.updates = []
    assert client.get(f"/api/v1/quantum/jobs/{job_id}").json()["status"] == "DONE"


def test_poll_unknown_job_is_404():
    client = _client(_FakeRunner())
    res = client.get("/api/v1/quantum/jobs/does-not-exist")
    assert res.status_code == 404


def test_quota_exhaustion_returns_429():
    client = _client(_FakeRunner(), max_per_hour=1, max_per_day=1)
    game_id = _game(client)
    assert client.post(f"/api/v1/games/{game_id}/quantum/hardware").status_code == 202
    res = client.post(f"/api/v1/games/{game_id}/quantum/hardware")
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "rate_limited"


def test_failed_submission_gives_the_quota_slot_back():
    from app.quantum.hardware import HardwareUnavailable

    runner = _FakeRunner(fail=HardwareUnavailable("no QPU today"))
    client = _client(runner, max_per_hour=1, max_per_day=1)
    game_id = _game(client)

    res = client.post(f"/api/v1/games/{game_id}/quantum/hardware")
    assert res.status_code == 503
    # a submission that never reached the QPU must not burn the hourly slot
    assert client.app.state.hardware_jobs.quota_snapshot() == (0, 0)


def test_info_reports_quota_usage():
    client = _client(_FakeRunner())
    client.post(f"/api/v1/games/{_game(client)}/quantum/hardware")
    body = client.get("/api/v1/quantum/hardware").json()
    assert body["jobs_last_hour"] == 1
    assert body["jobs_last_day"] == 1
