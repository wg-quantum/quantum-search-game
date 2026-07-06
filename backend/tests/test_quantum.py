import math

import numpy as np
import pytest

from app.quantum.backend import AerStatevectorBackend
from app.quantum.engine import optimal_iterations, run_grover


@pytest.fixture(scope="module")
def backend() -> AerStatevectorBackend:
    return AerStatevectorBackend()


def theory_prob(k: int, m: int, n: int) -> float:
    theta = math.asin(math.sqrt(m / n))
    return math.sin((2 * k + 1) * theta) ** 2


def test_optimal_iterations_known_values():
    assert optimal_iterations(1, 16) == 3
    assert optimal_iterations(1, 4096) == 50
    # more than half marked: already >50% at k=0
    assert optimal_iterations(3000, 4096) == 0


def test_optimal_iterations_invalid():
    with pytest.raises(ValueError):
        optimal_iterations(0, 16)
    with pytest.raises(ValueError):
        optimal_iterations(17, 16)


def test_grover_matches_theory_single_marked(backend):
    # N=16, M=1: exact match with sin^2((2k+1)theta) at every iteration
    result = run_grover(backend, marked=[5], iterations=4, n_qubits=4)
    for snap in result.snapshots:
        expected = theory_prob(snap.iteration, 1, 16)
        assert snap.marked_probability([5]) == pytest.approx(expected, abs=1e-9)


def test_grover_amplifies_uniformly_within_marked(backend):
    marked = [1, 6, 11]
    result = run_grover(backend, marked=marked, iterations=2, n_qubits=4)
    final = result.snapshots[-1].probabilities
    probs = final[marked]
    assert np.allclose(probs, probs[0])
    assert probs[0] > 1 / 16  # amplified above uniform


def test_over_rotation_decreases_probability(backend):
    result = run_grover(backend, marked=[3], iterations=6, n_qubits=4)
    p = [s.marked_probability([3]) for s in result.snapshots]
    k_opt = result.optimal  # == 3
    assert p[k_opt] == max(p)
    assert p[6] < p[k_opt]  # over-rotated past the peak


def test_unmarked_states_shrink_full_size(backend):
    # real size: 12 qubits, dictionary-scale candidate set
    marked = list(range(40))
    result = run_grover(backend, marked=marked, iterations=5, n_qubits=12)
    first, last = result.snapshots[0], result.snapshots[-1]
    unmarked_first = 1 - first.marked_probability(marked)
    unmarked_last = 1 - last.marked_probability(marked)
    assert unmarked_last < unmarked_first
    # probabilities always sum to 1
    for snap in result.snapshots:
        assert snap.probabilities.sum() == pytest.approx(1.0)


def test_iteration_bounds(backend):
    with pytest.raises(ValueError):
        run_grover(backend, marked=[0], iterations=-1, n_qubits=4)
    with pytest.raises(ValueError):
        run_grover(backend, marked=[0], iterations=201, n_qubits=4)


def test_empty_or_out_of_range_marked(backend):
    with pytest.raises(ValueError):
        run_grover(backend, marked=[], iterations=1, n_qubits=4)
    with pytest.raises(ValueError):
        run_grover(backend, marked=[16], iterations=1, n_qubits=4)
