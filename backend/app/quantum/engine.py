"""Grover engine: ties game candidates to the quantum backend.

Encoding: dictionary index i <-> computational basis state |i> on 12 qubits.
All 4096 states enter the initial superposition; indices >= dictionary size
(and non-candidate words) are never marked, so their amplitude shrinks —
which is itself part of the lesson.
"""

import math
from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np

from app.quantum.backend import QuantumBackend

N_QUBITS = 12
N_STATES = 1 << N_QUBITS
MAX_ITERATIONS = 200


def optimal_iterations(marked_count: int, n_states: int = N_STATES) -> int:
    """k* maximizing success probability sin^2((2k+1)theta), theta=asin(sqrt(M/N))."""
    if marked_count <= 0 or marked_count > n_states:
        raise ValueError("marked_count must be in [1, n_states]")
    theta = math.asin(math.sqrt(marked_count / n_states))
    return max(0, round(math.pi / (4 * theta) - 0.5))


@dataclass
class GroverSnapshot:
    iteration: int
    probabilities: np.ndarray  # shape (n_states,)

    def marked_probability(self, marked: Sequence[int]) -> float:
        return float(self.probabilities[list(marked)].sum())


@dataclass
class GroverResult:
    n_qubits: int
    n_states: int
    marked: list[int]
    optimal: int
    snapshots: list[GroverSnapshot]


def run_grover(
    backend: QuantumBackend,
    marked: Sequence[int],
    iterations: int,
    n_qubits: int = N_QUBITS,
) -> GroverResult:
    if not 0 <= iterations <= MAX_ITERATIONS:
        raise ValueError(f"iterations must be in [0, {MAX_ITERATIONS}]")
    distributions = backend.run_grover(n_qubits, marked, iterations)
    return GroverResult(
        n_qubits=n_qubits,
        n_states=1 << n_qubits,
        marked=list(marked),
        optimal=optimal_iterations(len(marked), 1 << n_qubits),
        snapshots=[
            GroverSnapshot(iteration=k, probabilities=p)
            for k, p in enumerate(distributions)
        ],
    )


MAX_SHOTS = 100


def measure(
    backend: QuantumBackend,
    marked: Sequence[int],
    iterations: int,
    shots: int = 1,
    n_qubits: int = N_QUBITS,
) -> dict[int, int]:
    """Sample the final Grover state. Returns {state index: count}."""
    if not 0 <= iterations <= MAX_ITERATIONS:
        raise ValueError(f"iterations must be in [0, {MAX_ITERATIONS}]")
    if not 1 <= shots <= MAX_SHOTS:
        raise ValueError(f"shots must be in [1, {MAX_SHOTS}]")
    return backend.sample(n_qubits, marked, iterations, shots)
