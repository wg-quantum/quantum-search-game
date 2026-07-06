import { useEffect, useState } from "react";
import { circuitApi } from "../api/client";
import type { CircuitResponse } from "../types";

/** Schematic Grover circuit rendered by Qiskit on the backend.
 *  Served as base64 <img> so the SVG never executes in our DOM. */
export function CircuitViewer({
  gameId,
  iterations,
}: {
  gameId: string;
  iterations: number;
}) {
  const [circuit, setCircuit] = useState<CircuitResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    circuitApi
      .get(gameId, iterations)
      .then((c) => { if (!cancelled) setCircuit(c); })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [gameId, iterations]);

  if (error) return <p className="text-xs text-tile-yellow">回路図を取得できませんでした</p>;
  if (!circuit) return <p className="text-xs text-muted">回路図を生成中…</p>;

  const src = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(circuit.svg)))}`;
  return (
    <figure>
      <div className="max-h-72 overflow-auto rounded-lg border border-line bg-ink p-2">
        <img src={src} alt={`Grover回路図 (${circuit.drawn_iterations}反復分)`} className="min-w-full" />
      </div>
      <figcaption className="mt-1 text-[11px] leading-relaxed text-muted">
        H⊗12 で全4096状態を重ね合わせ、Oracle + Diffusion を k = {circuit.iterations} 回反復
        {circuit.iterations > circuit.drawn_iterations &&
          `(図は最初の ${circuit.drawn_iterations} 回のみ)`}
        。これが Qiskit で実際に構成している回路の構造です。
      </figcaption>
    </figure>
  );
}
