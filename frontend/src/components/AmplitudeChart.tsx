import { fmtPct } from "../lib/grover";
import type { Snapshot } from "../types";

/** Horizontal bars for the top states of one snapshot. Bars animate via CSS width transition. */
export function AmplitudeChart({ snapshot }: { snapshot: Snapshot }) {
  const maxP = Math.max(snapshot.top[0]?.probability ?? 0, 1e-9);
  const shown = snapshot.top.slice(0, 12);

  return (
    <div className="flex flex-col gap-1" data-testid="amplitude-chart">
      {shown.map((s) => (
        <div key={s.index} className="flex items-center gap-2">
          <span className="w-14 shrink-0 text-right font-mono text-xs text-fg/80">
            {s.word ?? `|${s.index}⟩`}
          </span>
          <div className="h-4 flex-1 overflow-hidden rounded-sm bg-ink">
            <div
              className={`h-full transition-all duration-500 ${
                s.is_candidate
                  ? "bg-gradient-to-r from-cyan to-violet"
                  : "bg-tile-gray"
              }`}
              style={{ width: `${(s.probability / maxP) * 100}%` }}
            />
          </div>
          <span className="w-12 shrink-0 font-mono text-[10px] text-muted">
            {fmtPct(s.probability)}
          </span>
        </div>
      ))}
      <div className="flex items-center gap-2">
        <span className="w-14 shrink-0 text-right font-mono text-xs text-muted">
          その他
        </span>
        <span className="font-mono text-[10px] text-muted">
          合計 {fmtPct(snapshot.others_probability)}
        </span>
      </div>
    </div>
  );
}
