"""IBM Quantum hardware mode: a downscaled Grover run on a real QPU.

Why not just point the existing engine at a QPU? The game's oracle is a
12-qubit DiagonalGate over 4096 phases. Transpiled to a NISQ basis that is
tens of thousands of two-qubit gates deep, so the device returns noise —
docs/DESIGN.md D4 and the risk table already call this out, and no amount of
error mitigation rescues it.

What *is* meaningful on hardware is the same algorithm, downscaled. Take the
first few of the player's current candidates, re-index them into a small
register padded so that marked/total is about 1/4, and the optimal iteration
count drops to k* = 1 with an ideal success probability of ~95-100%. The
circuit is then a few dozen two-qubit gates — comfortably inside what current
devices do well. Because the ideal answer is ~certain, every bit of spread the
device shows is device noise, which is exactly the thing worth seeing.

The oracle here is built from multi-controlled Z rather than DiagonalGate:
same unitary (tests assert the distributions agree), but expressed in gates a
transpiler can map onto real coupling maps.
"""

import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from app.config import HardwareSettings
from app.quantum.backend import QuantumBackend
from app.quantum.engine import optimal_iterations

# Shortlist size and padding are the two knobs that keep the circuit shallow.
# marked/total == 1/PADDING_RATIO == 1/4 puts k* at 1 for every shortlist size
# we allow, so MAX_ITERATIONS is a guard rail rather than a real limit.
SHORTLIST_SIZE = 4
PADDING_RATIO = 4
MAX_ITERATIONS = 3


class HardwareUnavailable(RuntimeError):
    """Hardware mode is off, or the IBM Quantum service could not be reached."""


@dataclass(frozen=True)
class DownscaledProblem:
    """The small Grover instance that actually goes to the QPU."""

    n_qubits: int
    n_states: int
    marked: tuple[int, ...]  # basis states carrying a shortlisted word
    words: tuple[str, ...]  # words[i] is the word encoded at marked[i]
    dictionary_indices: tuple[int, ...]  # the 12-qubit indices they came from
    iterations: int

    def word_at(self, state: int) -> str | None:
        try:
            return self.words[self.marked.index(state)]
        except ValueError:
            return None


def downscale(
    candidate_indices: Sequence[int], words: Sequence[str]
) -> DownscaledProblem:
    """Map the head of the candidate list onto a small, hardware-sized register.

    Candidates arrive in dictionary order, which is frequency order, so the
    shortlist is the most common words still in play. Marked states are spread
    evenly across the register (stride = n_states // shortlist) so the result
    histogram reads as a comb rather than a clump at the left edge.
    """
    if not candidate_indices:
        raise ValueError("candidate_indices must not be empty")

    shortlist = tuple(candidate_indices[:SHORTLIST_SIZE])
    m = len(shortlist)
    # ceil(log2(m)) extra qubits for the shortlist, 2 more for the 1/4 padding
    n_qubits = (PADDING_RATIO.bit_length() - 1) + (m - 1).bit_length()
    n_states = 1 << n_qubits
    stride = n_states // m
    marked = tuple(i * stride for i in range(m))
    iterations = min(optimal_iterations(m, n_states), MAX_ITERATIONS)

    return DownscaledProblem(
        n_qubits=n_qubits,
        n_states=n_states,
        marked=marked,
        words=tuple(words[i] for i in shortlist),
        dictionary_indices=shortlist,
        iterations=iterations,
    )


def ideal_distribution(
    backend: QuantumBackend, problem: DownscaledProblem
) -> list[float]:
    """The noiseless distribution for the same problem, for side-by-side display."""
    distributions = backend.run_grover(
        problem.n_qubits, problem.marked, problem.iterations
    )
    return [float(p) for p in distributions[-1]]


# ---- circuit construction ----

def _mcz(qc: QuantumCircuit, n_qubits: int) -> None:
    """Phase flip on |1...1>, as H-MCX-H on the top qubit."""
    target = n_qubits - 1
    controls = list(range(target))
    if not controls:
        qc.z(target)
        return
    qc.h(target)
    qc.mcx(controls, target)
    qc.h(target)


def phase_oracle(n_qubits: int, marked: Sequence[int]) -> QuantumCircuit:
    """|x> -> -|x> for x in marked. Qubit q holds bit q of x (Qiskit order)."""
    qc = QuantumCircuit(n_qubits, name="Oracle")
    for state in marked:
        if not 0 <= state < (1 << n_qubits):
            raise ValueError(f"marked state {state} out of range for {n_qubits} qubits")
        zeros = [q for q in range(n_qubits) if not (state >> q) & 1]
        if zeros:
            qc.x(zeros)
        _mcz(qc, n_qubits)
        if zeros:
            qc.x(zeros)
    return qc


def diffuser(n_qubits: int) -> QuantumCircuit:
    """H^n (X^n MCZ X^n) H^n == -(2|s><s| - I); the global sign is unobservable."""
    qc = QuantumCircuit(n_qubits, name="Diffusion")
    qc.h(range(n_qubits))
    qc.x(range(n_qubits))
    _mcz(qc, n_qubits)
    qc.x(range(n_qubits))
    qc.h(range(n_qubits))
    return qc


def build_hardware_circuit(
    problem: DownscaledProblem, *, measure: bool = True
) -> QuantumCircuit:
    if not 0 <= problem.iterations <= MAX_ITERATIONS:
        raise ValueError(f"iterations must be in [0, {MAX_ITERATIONS}]")
    if not problem.marked:
        raise ValueError("marked set must not be empty")

    n = problem.n_qubits
    oracle = phase_oracle(n, problem.marked)
    diff = diffuser(n)

    qc = QuantumCircuit(n)
    qc.h(range(n))
    for _ in range(problem.iterations):
        qc.compose(oracle, inplace=True)
        qc.compose(diff, inplace=True)
    if measure:
        qc.measure_all()
    return qc


# ---- IBM Quantum runtime ----

@dataclass(frozen=True)
class Submission:
    job_id: str
    backend_name: str
    depth: int
    two_qubit_gates: int


@dataclass(frozen=True)
class JobUpdate:
    status: str  # INITIALIZING | QUEUED | RUNNING | DONE | CANCELLED | ERROR
    counts: dict[int, int] | None = None
    error: str | None = None
    qpu_seconds: float | None = None


TERMINAL_STATUSES = ("DONE", "CANCELLED", "ERROR")


def _counts_from_result(pub_result: object) -> dict[int, int]:
    """Counts keyed by basis-state integer, from whichever classical register exists."""
    data = getattr(pub_result, "data", None)
    if data is None:
        raise HardwareUnavailable("primitive result carried no data")
    bit_array = getattr(data, "meas", None)
    if bit_array is None:  # measure_all() names it "meas"; be tolerant anyway
        registers = list(data.values())
        if len(registers) != 1:
            raise HardwareUnavailable(
                f"expected one classical register, got {len(registers)}"
            )
        bit_array = registers[0]
    return {int(bits, 2): int(count) for bits, count in bit_array.get_counts().items()}


class IBMHardwareRunner:
    """Submits and polls SamplerV2 jobs. One instance per app, thread-safe.

    Service construction and backend selection both hit the network, so they
    are cached; the backend choice expires so that a device going offline does
    not wedge the app until restart.
    """

    BACKEND_TTL_SECONDS = 300.0

    def __init__(self, settings: HardwareSettings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._service: object | None = None
        self._backend: object | None = None
        self._backend_resolved_at = 0.0

    @property
    def settings(self) -> HardwareSettings:
        return self._settings

    @property
    def available(self) -> bool:
        return self._settings.enabled

    def _require_available(self) -> None:
        if not self._settings.enabled:
            raise HardwareUnavailable(
                "hardware mode is disabled (set IBM_QUANTUM_TOKEN to enable it)"
            )

    def _get_service(self) -> object:
        self._require_available()
        with self._lock:
            if self._service is None:
                try:
                    from qiskit_ibm_runtime import QiskitRuntimeService
                except ImportError as exc:  # pragma: no cover - packaging guard
                    raise HardwareUnavailable(
                        "qiskit-ibm-runtime is not installed"
                    ) from exc
                try:
                    self._service = QiskitRuntimeService(
                        channel=self._settings.channel,
                        token=self._settings.token,
                        instance=self._settings.instance,
                    )
                except Exception as exc:
                    raise HardwareUnavailable(
                        f"could not reach IBM Quantum: {exc}"
                    ) from exc
            return self._service

    def _get_backend(self, min_num_qubits: int) -> object:
        service = self._get_service()
        now = time.monotonic()
        with self._lock:
            fresh = now - self._backend_resolved_at < self.BACKEND_TTL_SECONDS
            if self._backend is not None and fresh:
                return self._backend
        try:
            if self._settings.backend_name:
                backend = service.backend(self._settings.backend_name)  # type: ignore[attr-defined]
            else:
                backend = service.least_busy(  # type: ignore[attr-defined]
                    min_num_qubits=min_num_qubits, simulator=False, operational=True
                )
        except Exception as exc:
            raise HardwareUnavailable(f"no usable QPU: {exc}") from exc
        with self._lock:
            self._backend = backend
            self._backend_resolved_at = time.monotonic()
        return backend

    def submit(self, problem: DownscaledProblem, shots: int) -> Submission:
        """Transpile and enqueue one Sampler job. Returns as soon as it is queued."""
        backend = self._get_backend(problem.n_qubits)
        from qiskit_ibm_runtime import SamplerV2

        circuit = build_hardware_circuit(problem)
        pass_manager = generate_preset_pass_manager(
            optimization_level=3, backend=backend
        )
        isa_circuit = pass_manager.run(circuit)
        try:
            job = SamplerV2(mode=backend).run([isa_circuit], shots=shots)
        except Exception as exc:
            raise HardwareUnavailable(f"job submission failed: {exc}") from exc

        ops = isa_circuit.count_ops()
        return Submission(
            job_id=job.job_id(),
            backend_name=getattr(backend, "name", str(backend)),
            depth=isa_circuit.depth(),
            two_qubit_gates=sum(
                count for name, count in ops.items() if name in _TWO_QUBIT_GATES
            ),
        )

    def poll(self, job_id: str) -> JobUpdate:
        service = self._get_service()
        try:
            job = service.job(job_id)  # type: ignore[attr-defined]
            status = str(job.status()).upper()
        except Exception as exc:
            raise HardwareUnavailable(f"could not read job {job_id}: {exc}") from exc

        if status not in TERMINAL_STATUSES:
            return JobUpdate(status=status)
        if status != "DONE":
            return JobUpdate(status=status, error=_error_message(job) or status)
        try:
            result = job.result()
        except Exception as exc:
            return JobUpdate(status="ERROR", error=f"result unavailable: {exc}")
        return JobUpdate(
            status="DONE",
            counts=_counts_from_result(result[0]),
            qpu_seconds=_qpu_seconds(job),
        )


_TWO_QUBIT_GATES = frozenset({"cx", "cz", "ecr", "cy", "ch", "swap", "rzz", "cp"})


def _error_message(job: object) -> str | None:
    getter = getattr(job, "error_message", None)
    if getter is None:
        return None
    try:
        message = getter()
    except Exception:  # pragma: no cover - best-effort diagnostics only
        return None
    return str(message) if message else None


def _qpu_seconds(job: object) -> float | None:
    """Billed QPU time, when the API reports it. Purely informational."""
    getter = getattr(job, "metrics", None)
    if getter is None:
        return None
    try:
        usage = (getter() or {}).get("usage") or {}
        seconds = usage.get("quantum_seconds", usage.get("seconds"))
        return float(seconds) if seconds is not None else None
    except Exception:  # pragma: no cover - best-effort diagnostics only
        return None
