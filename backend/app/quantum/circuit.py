"""Educational circuit diagram (display only).

The simulation circuit (backend.py) uses raw DiagonalGate for Aer's native
fast path; renaming those gates breaks Aer dispatch. So the diagram is built
separately with labeled opaque gates: H^n, then (Oracle, Diffusion) blocks.

Diagrams are drawn for at most MAX_DRAWN iterations; the frontend annotates
the actual repetition count.
"""

import io
from functools import lru_cache

import matplotlib

matplotlib.use("Agg")

from qiskit import QuantumCircuit
from qiskit.circuit import Gate

from app.quantum.engine import N_QUBITS

MAX_DRAWN = 3

_STYLE = {
    "backgroundcolor": "#00000000",
    "textcolor": "#e8eaf2",
    "linecolor": "#8b92a8",
    "gatetextcolor": "#0e1220",
    "displaytext": {},
    "displaycolor": {
        "Oracle": ("#5eead4", "#0e1220"),
        "Diffusion": ("#a78bfa", "#0e1220"),
        "h": ("#3a4055", "#e8eaf2"),
    },
}


def build_display_circuit(drawn_iterations: int, n_qubits: int = N_QUBITS) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits)
    qc.h(range(n_qubits))
    if drawn_iterations > 0:
        qc.barrier()
    for _ in range(drawn_iterations):
        qc.append(
            Gate(name="Oracle", num_qubits=n_qubits, params=[], label="Oracle"),
            range(n_qubits),
        )
        qc.append(
            Gate(name="Diffusion", num_qubits=n_qubits, params=[], label="Diffusion"),
            range(n_qubits),
        )
        qc.barrier()
    return qc


@lru_cache(maxsize=MAX_DRAWN + 1)
def circuit_svg(drawn_iterations: int, n_qubits: int = N_QUBITS) -> str:
    """SVG of the schematic Grover circuit. Cached: only MAX_DRAWN+1 variants exist."""
    if not 0 <= drawn_iterations <= MAX_DRAWN:
        raise ValueError(f"drawn_iterations must be in [0, {MAX_DRAWN}]")
    qc = build_display_circuit(drawn_iterations, n_qubits)
    fig = qc.draw("mpl", fold=-1, style=_STYLE)
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    import matplotlib.pyplot as plt

    plt.close(fig)
    return buf.getvalue()
