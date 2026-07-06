import { useEffect, useRef, useState } from "react";
import { quantumApi } from "../api/client";
import { fmtPct, sliderMax } from "../lib/grover";
import type { MeasureResult, QuantumRunResponse } from "../types";
import { AmplitudeChart } from "./AmplitudeChart";
import { CircuitViewer } from "./CircuitViewer";

/** P(candidates) over iterations, with a marker at the optimum. */
function ProbabilitySparkline({
  values,
  cursor,
  optimal,
}: {
  values: number[];
  cursor: number;
  optimal: number;
}) {
  const w = 260;
  const h = 56;
  const n = values.length;
  const x = (i: number) => (n <= 1 ? 0 : (i / (n - 1)) * w);
  const y = (p: number) => h - p * (h - 4) - 2;
  const points = values.map((p, i) => `${x(i)},${y(p)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img" aria-label="反復ごとの候補確率">
      {optimal < n && (
        <line
          x1={x(optimal)} y1={0} x2={x(optimal)} y2={h}
          stroke="var(--color-violet)" strokeDasharray="3 3" strokeWidth="1"
        />
      )}
      <polyline points={points} fill="none" stroke="var(--color-cyan)" strokeWidth="1.5" />
      <circle cx={x(cursor)} cy={y(values[cursor] ?? 0)} r="3.5" fill="var(--color-cyan)" />
    </svg>
  );
}

export function QuantumLab({
  gameId,
  candidateCount,
  guessCount,
  playing,
  onSuggest,
}: {
  gameId: string;
  candidateCount: number;
  guessCount: number;
  playing: boolean;
  onSuggest: (word: string) => void;
}) {
  const [iterations, setIterations] = useState(2);
  const [result, setResult] = useState<QuantumRunResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [measured, setMeasured] = useState<MeasureResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCircuit, setShowCircuit] = useState(false);
  const timer = useRef<number | null>(null);

  // A new guess changes the oracle: previous results no longer apply.
  useEffect(() => {
    if (timer.current) window.clearInterval(timer.current);
    setResult(null);
    setMeasured(null);
    setCursor(0);
  }, [gameId, guessCount]);

  useEffect(() => () => { if (timer.current) window.clearInterval(timer.current); }, []);

  const max = sliderMax(result?.optimal_iterations ?? 50);

  const run = async () => {
    if (running) return;
    setRunning(true);
    setError(null);
    setMeasured(null);
    if (timer.current) window.clearInterval(timer.current);
    try {
      const res = await quantumApi.run(gameId, iterations);
      setResult(res);
      setCursor(0);
      // play through iterations
      let k = 0;
      timer.current = window.setInterval(() => {
        k += 1;
        if (k >= res.snapshots.length - 1) {
          if (timer.current) window.clearInterval(timer.current);
          k = res.snapshots.length - 1;
        }
        setCursor(k);
      }, 450);
    } catch (e) {
      setError(e instanceof Error ? e.message : "実行に失敗しました");
    } finally {
      setRunning(false);
    }
  };

  const doMeasure = async () => {
    setError(null);
    try {
      const res = await quantumApi.measure(gameId, iterations, 1);
      setMeasured(res.results[0] ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "測定に失敗しました");
    }
  };

  const snap = result?.snapshots[cursor];
  const probs = result?.snapshots.map((s) => s.candidate_probability) ?? [];

  return (
    <aside className="flex w-full flex-col gap-4 rounded-xl border border-line bg-surface p-5 lg:w-80">
      <div className="flex items-baseline justify-between">
        <h2 className="font-display text-sm font-bold tracking-widest text-muted uppercase">
          Grover Lab
        </h2>
        <span className="font-mono text-xs text-muted">G = D·O</span>
      </div>

      <p className="text-xs leading-relaxed text-muted">
        Oracle は候補 {candidateCount.toLocaleString()} 語の位相を反転し、Diffusion
        がその振幅を増幅します。反復しすぎると確率は再び下がります(over-rotation)。
      </p>

      <div>
        <label className="flex items-baseline justify-between text-xs">
          <span className="text-muted">反復回数 k</span>
          <span className="font-mono">
            {iterations}
            {result && (
              <span className="text-muted"> / 最適 k* = {result.optimal_iterations}</span>
            )}
          </span>
        </label>
        <input
          type="range"
          min={0}
          max={max}
          value={Math.min(iterations, max)}
          onChange={(e) => setIterations(Number(e.target.value))}
          className="w-full accent-(--color-cyan)"
          aria-label="Grover反復回数"
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => void run()}
          disabled={running}
          className="flex-1 rounded-md bg-gradient-to-r from-cyan to-violet px-3 py-2 font-display text-sm font-bold text-ink hover:brightness-110 focus-visible:outline-2 focus-visible:outline-cyan disabled:opacity-50"
        >
          {running ? "実行中…" : "Grover を実行"}
        </button>
        <button
          onClick={() => void doMeasure()}
          disabled={running || !result}
          className="rounded-md border border-line px-3 py-2 font-display text-sm font-bold hover:bg-ink focus-visible:outline-2 focus-visible:outline-cyan disabled:opacity-40"
        >
          測定
        </button>
      </div>

      {error && <p className="text-xs text-tile-yellow">{error}</p>}

      {result && snap && (
        <>
          <div className="flex items-baseline justify-between">
            <span className="font-mono text-xs text-muted">k = {snap.iteration}</span>
            <span className="font-mono text-sm">
              P(候補) = <span className="text-cyan">{fmtPct(snap.candidate_probability)}</span>
            </span>
          </div>
          <ProbabilitySparkline
            values={probs}
            cursor={cursor}
            optimal={result.optimal_iterations}
          />
          <input
            type="range"
            min={0}
            max={result.snapshots.length - 1}
            value={cursor}
            onChange={(e) => setCursor(Number(e.target.value))}
            className="w-full accent-(--color-violet)"
            aria-label="表示する反復"
          />
          <AmplitudeChart snapshot={snap} />
          <button
            onClick={() => setShowCircuit((v) => !v)}
            className="self-start font-mono text-xs text-muted underline decoration-dotted underline-offset-4 hover:text-cyan focus-visible:outline-2 focus-visible:outline-cyan"
          >
            {showCircuit ? "回路図を閉じる" : "回路図を見る"}
          </button>
          {showCircuit && (
            <CircuitViewer gameId={gameId} iterations={result.iterations} />
          )}
        </>
      )}

      {measured && (
        <div key={measured.index + "-" + measured.count} className="measure-pop rounded-lg border border-line bg-ink p-3 text-center">
          <p className="text-[10px] tracking-widest text-muted uppercase">測定結果</p>
          <p className="font-mono text-2xl font-bold tracking-widest uppercase">
            {measured.word ?? `|${measured.index}⟩`}
          </p>
          {measured.word === null && (
            <p className="mt-1 text-[11px] text-muted">
              辞書外の状態を引きました。量子測定は確率的です — もう一度どうぞ。
            </p>
          )}
          {!measured.is_candidate && measured.word && (
            <p className="mt-1 text-[11px] text-muted">候補外の語でした(確率は小さくてもゼロではない)</p>
          )}
          {measured.word && playing && (
            <button
              onClick={() => onSuggest(measured.word!)}
              className="mt-2 rounded-md border border-cyan px-3 py-1 font-display text-xs font-bold text-cyan hover:bg-cyan hover:text-ink focus-visible:outline-2 focus-visible:outline-cyan"
            >
              この単語を入力欄へ
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
