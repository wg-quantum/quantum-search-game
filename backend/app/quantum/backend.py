"""Quantum backend abstraction.

AerStatevectorBackend is the default. An IBM Quantum backend can be added
later by implementing the same Protocol (Phase 5, optional).

The oracle is a phase oracle over the *candidate set*: it flips the sign of
every basis state whose index is a word consistent with all feedback so far.
Grover then amplifies those states uniformly. It never knows the answer.
"""

from collections.abc import Sequence
from typing import Protocol

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import DiagonalGate
from qiskit_aer import AerSimulator


class QuantumBackend(Protocol):
    def run_grover(
        self, n_qubits: int, marked: Sequence[int], iterations: int
    ) -> list[np.ndarray]:
        """Run Grover and return per-iteration probability distributions.

        Returns iterations+1 arrays of shape (2**n_qubits,):
        index 0 is the initial uniform superposition, index k is the state
        after k Grover iterations (oracle + diffusion).
        """
        ...

    def sample(
        self, n_qubits: int, marked: Sequence[int], iterations: int, shots: int
    ) -> dict[int, int]:
        """Measure the final Grover state. Returns {state index: count}."""
        ...


class AerStatevectorBackend:
    def __init__(self, seed: int | None = None) -> None:
        self._sim = AerSimulator(method="statevector", seed_simulator=seed)

    def _grover_circuit(
        self, n_qubits: int, marked: Sequence[int], iterations: int
    ) -> QuantumCircuit:
        n_states = 1 << n_qubits
        if not marked:
            raise ValueError("marked set must not be empty")
        if max(marked) >= n_states or min(marked) < 0:
            raise ValueError("marked index out of range")

        # Phase oracle: |x> -> -|x> for x in candidate set
        # (do not rename the gate: Aer dispatches natively on name "diagonal")
        oracle_diag = np.ones(n_states, dtype=complex)
        oracle_diag[list(marked)] = -1
        oracle = DiagonalGate(oracle_diag.tolist())

        # Reflection about |0...0>: diag(1,-1,...,-1) == 2|0><0| - I
        refl0_diag = -np.ones(n_states, dtype=complex)
        refl0_diag[0] = 1
        refl0 = DiagonalGate(refl0_diag.tolist())

        qubits = range(n_qubits)
        qc = QuantumCircuit(n_qubits)
        qc.h(qubits)
        qc.save_statevector(label="iter_0")
        for k in range(1, iterations + 1):
            qc.append(oracle, qubits)
            # Diffusion: H^n (2|0><0| - I) H^n = 2|s><s| - I
            qc.h(qubits)
            qc.append(refl0, qubits)
            qc.h(qubits)
            qc.save_statevector(label=f"iter_{k}")
        return qc

    def run_grover(
        self, n_qubits: int, marked: Sequence[int], iterations: int
    ) -> list[np.ndarray]:
        qc = self._grover_circuit(n_qubits, marked, iterations)
        data = self._sim.run(qc).result().data(0)
        return [
            np.abs(np.asarray(data[f"iter_{k}"])) ** 2
            for k in range(iterations + 1)
        ]

    def sample(
        self, n_qubits: int, marked: Sequence[int], iterations: int, shots: int
    ) -> dict[int, int]:
        qc = self._grover_circuit(n_qubits, marked, iterations)
        qc.measure_all()
        counts = self._sim.run(qc, shots=shots).result().get_counts()
        # bitstring "q_{n-1}...q_0" -> integer state index
        return {int(bits, 2): count for bits, count in counts.items()}
