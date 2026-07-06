/**
 * The pedagogical heart of the app: the shrinking candidate set.
 * In Phase 3 this set becomes exactly what the Grover oracle marks,
 * and the meter evolves into a probability distribution.
 */
export function CandidatePanel({
  count,
  total,
  words,
}: {
  count: number;
  total: number;
  words: string[];
}) {
  // log scale: linear width would be invisible once candidates < ~100
  const ratio =
    count <= 1 ? 0 : Math.log(count) / Math.log(Math.max(total, 2));

  return (
    <aside className="flex w-full flex-col gap-4 rounded-xl border border-line bg-surface p-5 lg:w-80">
      <div className="flex items-baseline justify-between">
        <h2 className="font-display text-sm font-bold tracking-widest text-muted uppercase">
          候補空間
        </h2>
        <span className="font-mono text-xs text-muted">|ψ⟩</span>
      </div>

      <div>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-4xl font-bold" data-testid="candidate-count">
            {count.toLocaleString()}
          </span>
          <span className="font-mono text-sm text-muted">/ {total.toLocaleString()} 語</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyan to-violet transition-all duration-700"
            style={{ width: `${Math.max(ratio * 100, count > 0 ? 2 : 0)}%` }}
          />
        </div>
        <p className="mt-1 text-right font-mono text-[10px] text-muted">log scale</p>
      </div>

      <p className="text-xs leading-relaxed text-muted">
        推測のたびに、フィードバックと矛盾する語が候補から消えます。この集合こそが、次のフェーズで
        <span className="text-cyan"> Oracle がマークする状態</span>です。
      </p>

      {words.length > 0 && (
        <div className="flex max-h-56 flex-wrap content-start gap-1.5 overflow-y-auto">
          {words.map((w) => (
            <span
              key={w}
              className="rounded bg-ink px-2 py-0.5 font-mono text-xs text-fg/80"
            >
              {w}
            </span>
          ))}
          {count > words.length && (
            <span className="px-2 py-0.5 font-mono text-xs text-muted">
              +{(count - words.length).toLocaleString()}
            </span>
          )}
        </div>
      )}
    </aside>
  );
}
